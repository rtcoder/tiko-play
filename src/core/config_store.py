import asyncio
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4
from pydantic import ValidationError
from src.core.models import AppConfig, AppError, ConfigSnapshot

class ConfigStore:
    def __init__(self, path: Path):
        self.path=path
        self._snapshot=None
        self.error=None
        self.recovery_data=None
        self._lock=asyncio.Lock()
        self._future=False
    def snapshot(self):
        if self._snapshot is None:
            raise self.error or AppError('configuration_unavailable','Konfiguracja nie jest gotowa',status=409)
        return ConfigSnapshot(self._snapshot.config.model_copy(deep=True),self._snapshot.revision)
    def _read(self):
        if not self.path.exists(): return AppConfig(),None
        raw=self.path.read_bytes()
        data=json.loads(raw)
        self.recovery_data=data
        if not isinstance(data,dict): raise ValueError('Konfiguracja musi być obiektem JSON')
        if data.get('version',1) not in (1,2):
            self._future=True
            raise AppError('future_version','Ta konfiguracja wymaga innej wersji TikoPlay',status=409)
        legacy=data.get('version',1)==1
        if legacy:
            data={**data,'version':2,'mappings':[{**m,'id':m.get('id') or str(uuid4())} for m in data.get('mappings',[])]}
        return AppConfig.model_validate(data),raw if legacy else None
    async def load(self):
        async with self._lock:
            try:
                cfg,backup=await asyncio.to_thread(self._read)
                if backup is not None or not self.path.exists():
                    await asyncio.to_thread(self._write,cfg,backup,False)
                self._snapshot=ConfigSnapshot(cfg,1)
                self.error=None
                return self.snapshot()
            except Exception as exc:
                self.error=self._error(exc)
                raise self.error from exc
    def _error(self,exc):
        if isinstance(exc,AppError): return exc
        if isinstance(exc,ValidationError):
            fields={'.'.join(map(str,e['loc'])):e['msg'] for e in exc.errors()}
        else: fields={}
        return AppError('configuration_error','Nie można odczytać lub zapisać konfiguracji. Sprawdź plik i uprawnienia.',fields,422)
    def _write(self,config,backup=None,recovery=False):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if backup is not None:
            target=self.path.with_name('config.v1.backup.json')
            if recovery: target=self.path.with_name(f'config.recovery.{uuid4().hex}.json')
            try:
                with target.open('xb') as f: f.write(backup);f.flush();os.fsync(f.fileno())
            except FileExistsError:
                if recovery: raise
        fd,name=tempfile.mkstemp(prefix='.config-',suffix='.tmp',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(config.model_dump_json(indent=2));f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            if os.path.exists(name): os.unlink(name)
    async def save(self,config,expected_revision):
        async with self._lock:
            old=self.snapshot()
            if old.revision!=expected_revision: raise AppError('revision_conflict','Konfiguracja została zmieniona w innym panelu',status=409)
            try: await asyncio.to_thread(self._write,config)
            except Exception as exc: raise self._error(exc) from exc
            self._snapshot=ConfigSnapshot(config.model_copy(deep=True),old.revision+1)
            return self.snapshot()
    async def repair(self,config):
        async with self._lock:
            if self._future: raise AppError('future_version','Użyj wersji obsługującej ten plik',status=409)
            if self._snapshot is not None: raise AppError('not_recovery','Konfiguracja nie wymaga naprawy',status=409)
            try:
                raw=await asyncio.to_thread(self.path.read_bytes) if self.path.exists() else None
                await asyncio.to_thread(self._write,config,raw,True)
            except Exception as exc: raise self._error(exc) from exc
            self._snapshot=ConfigSnapshot(config,1);self.error=None;self.recovery_data=None
            return self.snapshot()

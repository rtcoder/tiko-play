from src.core.output_guard import TargetIdentity


class MacFocus:
    @staticmethod
    def identity(app):
        if (
            app is None
            or app.isTerminated()
            or not app.launchDate()
            or not app.bundleURL()
        ):
            return None
        return TargetIdentity(
            app=str(app.bundleURL().path()),
            pid=int(app.processIdentifier()),
            started=str(app.launchDate().timeIntervalSince1970()),
            name=str(app.localizedName() or "Application")[:256],
        )

    def current_target(self):
        import AppKit
        import objc

        with objc.autorelease_pool():
            return self.identity(
                AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
            )

    def targets(self):
        import os

        import AppKit
        import objc

        with objc.autorelease_pool():
            return [
                identity
                for app in AppKit.NSWorkspace.sharedWorkspace().runningApplications()
                if app.activationPolicy() == 0
                and app.processIdentifier() != os.getpid()
                and (identity := self.identity(app)) is not None
            ]

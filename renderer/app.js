const fs = require('fs');
const path = require('path');

const configPath = path.join(__dirname, '..', 'config.json');

document.getElementById('saveBtn').addEventListener('click', () => {
    const streamerId = document.getElementById('streamerId').value.trim();
    if (!streamerId) {
        alert('Podaj ID streamera!');
        return;
    }

    const config = {
        streamerId
    };

    fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    alert('Zapisano streamer ID!');
    // Tu można przekierować do kolejnego widoku
});

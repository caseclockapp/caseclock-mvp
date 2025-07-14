// 🛠️ Fix for OpenAI + Node file uploads
const { File } = require('node:buffer');
globalThis.File = File;

const fs = require('fs');
const os = require('os');
require('dotenv').config();
const { app, Menu, Tray } = require('electron');
const path = require('path');
const recorder = require('node-record-lpcm16');
const { OpenAI } = require('openai');

let tray = null;
let isRecording = false;

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

async function transcribeAudio(audioBuffer) {
  try {
    const tempPath = path.join(os.tmpdir(), 'temp_audio.wav');
    fs.writeFileSync(tempPath, audioBuffer);
    console.log('📤 Sending audio to OpenAI...');

    const response = await openai.audio.transcriptions.create({
      file: fs.createReadStream(tempPath),
      model: 'whisper-1',
    });

    console.log('📥 Transcription response:', response);
    return response.text;
  } catch (error) {
    console.error('❌ Transcription error:', error);
    return null;
  }
}

function listenAndTrigger() {
  if (isRecording) return;

  isRecording = true;
  console.log("🎙️ Listening... Say something like 'Start billing Johnson case'");

  const chunks = [];

  const recording = recorder
    .record({
      sampleRateHertz: 16000,
      threshold: 0,
      verbose: false,
      recordProgram: 'sox',
      silence: '1.0',
      endOnSilence: true,
    })
    .stream()
    .on('data', (chunk) => chunks.push(chunk))
    .on('end', async () => {
      const audioBuffer = Buffer.concat(chunks);
      const command = await transcribeAudio(audioBuffer);

      if (command) {
        console.log('🧠 Heard:', command);
        if (command.toLowerCase().includes('start')) {
          console.log('✅ Timer started');
        } else if (command.toLowerCase().includes('stop')) {
          console.log('⛔ Timer stopped');
        } else {
          console.log('🤷‍♀️ No recognized action.');
        }
      } else {
        console.log('❌ No command recognized.');
      }

      isRecording = false;
    });

  setTimeout(() => recording.emit('end'), 5000);
}

app.whenReady().then(() => {
  tray = new Tray(path.join(__dirname, 'assets/trayTemplate.png'));
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Start Listening', click: listenAndTrigger },
    { label: 'Quit', click: () => app.quit() },
  ]);
  tray.setToolTip('CaseClock');
  tray.setContextMenu(contextMenu);
});
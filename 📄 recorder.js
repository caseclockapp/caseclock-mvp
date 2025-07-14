const recorder = require('node-record-lpcm16');
const fs = require('fs');
const axios = require('axios');
const FormData = require('form-data');
require('dotenv').config();

const recordAndTranscribe = async () => {
  const filePath = 'recording.wav';
  const file = fs.createWriteStream(filePath, { encoding: 'binary' });

  const recording = recorder.record({
    sampleRate: 16000,
    threshold: 0.5,
    verbose: false,
    recordProgram: 'sox',
    silence: '1.0',
  });

  console.log('🎤 Recording for 5 seconds...');
  recording.stream().pipe(file);

  setTimeout(async () => {
    recording.stop();
    console.log('🛑 Recording stopped.');

    const formData = new FormData();
    formData.append('file', fs.createReadStream(filePath));
    formData.append('model', 'whisper-1');

    try {
      const response = await axios.post('https://api.openai.com/v1/audio/transcriptions', formData, {
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          ...formData.getHeaders()
        }
      });

      const transcript = response.data.text;
      console.log('📝 Transcription:', transcript);
      fs.appendFileSync('transcriptions.log', `${new Date().toISOString()}: ${transcript}\n`);
    } catch (error) {
      console.error('❌ Error transcribing:', error.response?.data || error.message);
    }
  }, 5000);
};

module.exports = { recordAndTranscribe };

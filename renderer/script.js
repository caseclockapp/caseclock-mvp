
let currentCase = "";
let startTime = null;

function startListening() {
  if (!('webkitSpeechRecognition' in window)) {
    alert("Your browser doesn't support speech recognition");
    return;
  }
  const recognition = new webkitSpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onresult = function(event) {
    const command = event.results[0][0].transcript.toLowerCase();
    document.getElementById("status").textContent = `Heard: ${command}`;
    handleCommand(command);
  };
  recognition.start();
}

function handleCommand(command) {
  if (command.startsWith("start billing for")) {
    currentCase = command.replace("start billing for", "").trim();
    startTime = new Date();
    document.getElementById("status").textContent = `Started billing for ${currentCase}`;
  } else if (command.startsWith("stop billing")) {
    if (currentCase && startTime) {
      const endTime = new Date();
      const duration = Math.round((endTime - startTime) / 1000);
      const taskType = prompt("What was this task? (e.g., briefing, meeting, prep)");
      const entry = `${new Date().toISOString().split('T')[0]},${currentCase},${startTime.toLocaleTimeString()},${endTime.toLocaleTimeString()},${duration},${taskType}`;
      saveLog(entry);
      currentCase = "";
      startTime = null;
    } else {
      document.getElementById("status").textContent = "No active case to stop.";
    }
  }
}

function saveLog(entry) {
  const fs = require('fs');
  const logPath = require('path').join(__dirname, '..', 'logs.csv');
  if (!fs.existsSync(logPath)) {
    fs.writeFileSync(logPath, "Date,Case,Start Time,End Time,Duration (s),Task Type\n");
  }
  fs.appendFileSync(logPath, entry + "\n");
  const li = document.createElement("li");
  li.textContent = entry;
  document.getElementById("log").appendChild(li);
}

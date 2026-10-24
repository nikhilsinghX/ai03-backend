// Voice helpers are intentionally isolated for the next interview-loop stage.
// Chrome Web Speech APIs require a secure origin (localhost is supported).
(() => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  window.InterviewSpeech = {
    supported: Boolean(SpeechRecognition),
    speak(text) {
      if (!('speechSynthesis' in window)) return false;
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.96;
      window.speechSynthesis.speak(utterance);
      return true;
    },
    listen({ onText, onError, onEnd } = {}) {
      if (!SpeechRecognition) { onError?.(new Error('Speech recognition is not supported in this browser. Use typed answers.')); return null; }
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-IN'; recognition.interimResults = true; recognition.continuous = false;
      recognition.onresult = event => { let text = ''; let final = false; for (let i = 0; i < event.results.length; i++) { text += event.results[i][0].transcript; final = final || event.results[i].isFinal; } onText?.(text.trim(), final); };
      recognition.onerror = event => onError?.(new Error(event.error || 'Speech recognition failed'));
      recognition.onend = () => onEnd?.(); recognition.start(); return recognition;
    },
    stop() { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }
  };
})();

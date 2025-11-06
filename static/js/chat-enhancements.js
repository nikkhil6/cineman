// Small client-side enhancements for chat interactivity:
// - quick-suggestions click handling
// - simple simulated typing indicator (replace with streaming from backend)
// - toggle for dark panel (optional)
// You should wire actual network calls to your chat API where indicated.

(function(){
    const form = document.getElementById('chatForm');
    const input = document.getElementById('messageInput');
    const box = document.getElementById('chatBox');
    const sendBtn = document.getElementById('sendBtn');
    const suggestions = document.getElementById('suggestions');
  
    // helper to append message nodes
    function appendMsg(text, cls='user'){
      const d = document.createElement('div');
      d.className = 'msg ' + (cls==='user' ? 'user' : 'cineman');
      d.textContent = text;
      box.appendChild(d);
      box.scrollTop = box.scrollHeight - box.clientHeight;
    }
  
    // simple typing indicator displayed as a message then replaced by the answer
    function showTypingThenReplace(answerText){
      const typing = document.createElement('div');
      typing.className = 'msg cineman typing';
      typing.textContent = 'CineMan is thinking...';
      box.appendChild(typing);
      box.scrollTop = box.scrollHeight;
      // simulate thinking; in production, replace with streaming response and incremental updates
      setTimeout(()=>{
        typing.remove();
        appendMsg(answerText, 'cineman');
      }, 1000 + Math.random()*900);
    }
  
    // wire suggestion chips
    suggestions?.addEventListener('click', (e)=>{
      const chip = e.target.closest('.chip');
      if(!chip) return;
      const text = chip.textContent.trim();
      input.value = text;
      input.focus();
    });
  
    // send flow (demo). Replace fetch call with real API endpoint.
    sendBtn.addEventListener('click', sendMessage);
    form.addEventListener('submit', (ev)=>{ sendMessage(); ev.preventDefault(); });
  
    function sendMessage(){
      const text = input.value.trim();
      if(!text) return;
      appendMsg(text, 'user');
      input.value = '';
      input.blur();
  
      // Simulated backend call. Replace this block with real API call:
      // fetch('/api/chat', { method:'POST', body: JSON.stringify({text}) ... })
      //   .then(stream / json).then(render incremental streaming)
      // For demo we generate a canned reply:
      showTypingThenReplace(`Here are 3 picks for "${text}":\n1) Example Movie A (2020) — Why it fits...\n2) Example Movie B (2018) — Why it fits...\n3) Example Movie C (2023) — Why it fits...`);
    }
  
    // small UX: long-press on background toggles dark panel (optional)
    let longPressTimer;
    document.querySelector('.chat-container').addEventListener('touchstart', (e)=>{
      longPressTimer = setTimeout(()=> {
        document.querySelector('.chat-box').classList.toggle('dark');
      }, 800);
    });
    document.querySelector('.chat-container').addEventListener('touchend', ()=> clearTimeout(longPressTimer));
  
  })();
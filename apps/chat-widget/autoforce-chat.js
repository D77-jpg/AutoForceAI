/* AutoForceAI chat widget. Embed:
<script src="http://localhost:8010/widget/autoforce-chat.js" data-api="http://localhost:8010"></script>
*/
(function(){
  var script = document.currentScript;
  var API = (script && script.getAttribute("data-api")) || "http://localhost:8010";
  var BOT = (script && script.getAttribute("data-bot-id")) || "";
  var KEY = "af_chat_sid";
  function el(tag, cls, html){ var n=document.createElement(tag); if(cls) n.className=cls; if(html) n.innerHTML=html; return n; }
  var btn = el("button");
  btn.textContent = "Chat";
  btn.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:99999;background:#4f46e5;color:#fff;border:0;border-radius:999px;padding:12px 18px;cursor:pointer;font:14px/1 sans-serif;";
  var box = el("div");
  box.style.cssText = "display:none;position:fixed;right:20px;bottom:70px;width:340px;height:460px;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:12px;z-index:99999;flex-direction:column;overflow:hidden;font:13px/1.4 sans-serif;";
  box.innerHTML = '<div style="padding:10px 12px;background:#1e293b;font-weight:600">Sales Assistant</div><div id="af-msgs" style="flex:1;overflow:auto;padding:10px;height:350px"></div><form id="af-form" style="display:flex;border-top:1px solid #334155"><input id="af-input" style="flex:1;background:#0b1220;border:0;color:#fff;padding:10px" placeholder="Ask about MOQ / price..."/><button style="background:#4f46e5;border:0;color:#fff;padding:0 12px">Send</button></form>';
  document.body.appendChild(btn); document.body.appendChild(box);
  var msgs = box.querySelector("#af-msgs");
  function add(role, text){ var d=el("div"); d.style.margin="8px 0"; d.style.whiteSpace="pre-wrap"; d.textContent=(role==="user"?"You: ":"AI: ")+text; msgs.appendChild(d); msgs.scrollTop=msgs.scrollHeight; }
  var sid = localStorage.getItem(KEY);
  async function ensure(){
    if (sid) return sid;
    var res = await fetch(API+"/api/v1/service/widget/start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({bot_id: BOT? Number(BOT): null})});
    var data = await res.json();
    sid = data.session_uuid; localStorage.setItem(KEY, sid);
    add("assistant", data.welcome || "Hello!");
    return sid;
  }
  btn.onclick = async function(){ box.style.display = box.style.display==="none" ? "flex" : "none"; if(box.style.display==="flex") await ensure(); };
  box.querySelector("#af-form").onsubmit = async function(e){
    e.preventDefault();
    var input = box.querySelector("#af-input");
    var text = input.value.trim(); if(!text) return;
    input.value=""; add("user", text);
    await ensure();
    var res = await fetch(API+"/api/v1/service/widget/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_uuid:sid,message:text})});
    var data = await res.json();
    add("assistant", data.reply || "");
  };
})();

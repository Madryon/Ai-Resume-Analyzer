const $=id=>document.getElementById(id);
let latestAnswer="";

function escapeHtml(s){return s.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}

function markdownLite(text){
  const blocks=[];
  let t=text.replace(/```(?:[\w#+.-]+)?\n?([\s\S]*?)```/g,(_,code)=>{
    const key=`@@CODE${blocks.length}@@`;
    blocks.push(`<pre><code>${escapeHtml(code.trim())}</code></pre>`);
    return key;
  });
  t=escapeHtml(t)
    .replace(/^### (.*)$/gm,"<h4>$1</h4>")
    .replace(/^## (.*)$/gm,"<h3>$1</h3>")
    .replace(/^# (.*)$/gm,"<h3>$1</h3>")
    .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
    .replace(/`([^`\n]+)`/g,"<code>$1</code>")
    .replace(/^\s*[-*] (.*)$/gm,"<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g,m=>`<ul>${m}</ul>`)
    .replace(/\n{2,}/g,"</p><p>")
    .replace(/\n/g,"<br>");
  t=`<p>${t}</p>`;
  blocks.forEach((b,i)=>t=t.replace(`@@CODE${i}@@`,b));
  return t;
}

async function loadModels(){
  try{
    const r=await fetch("/api/health"),data=await r.json();
    if(!data.ok)throw new Error();
    $("status").className="status online";
    $("status").innerHTML="<span></span> API connected";
  }catch{
    $("status").className="status offline";
    $("status").innerHTML="<span></span> API unavailable";
  }
}

async function analyze(){
  const file=$("resumeFile").files[0];
  const text=$("resumeText").value.trim();
  if(!file&&!text){
    $("result").innerHTML='<div class="error">Upload a resume or paste resume text first.</div>';
    return;
  }

  const fd=new FormData();
  fd.append("resume_text",text);
  fd.append("job_description",$("jobDescription").value);
  fd.append("mode",$("mode").value);
  fd.append("level",$("level").value);
  fd.append("model",$("model").value);
  if(file)fd.append("resume_file",file);

  $("analyzeBtn").disabled=true;
  $("copyBtn").disabled=true;
  $("downloadBtn").disabled=true;
  $("loading").classList.remove("hidden");
  $("result").innerHTML="";
  $("meta").textContent="AI is analyzing…";

  try{
    const r=await fetch("/api/analyze",{method:"POST",body:fd});
    const data=await r.json();
    if(!r.ok)throw new Error(data.error||"Analysis failed.");
    latestAnswer=data.answer||"";
    $("result").innerHTML=markdownLite(latestAnswer);
    $("meta").textContent=`${data.model} • ${data.input_tokens} in / ${data.output_tokens} out tokens`;
    $("copyBtn").disabled=false;
    $("downloadBtn").disabled=false;
    saveHistory(data);
  }catch(e){
    $("result").innerHTML=`<div class="error"><strong>Could not analyze.</strong><br>${escapeHtml(e.message)}</div>`;
    $("meta").textContent="Request failed";
  }finally{
    $("loading").classList.add("hidden");
    $("analyzeBtn").disabled=false;
  }
}

function saveHistory(data){
  const h=JSON.parse(localStorage.getItem("resumepilot_history")||"[]");
  h.unshift({
    answer:data.answer,
    mode:$("mode").value,
    model:data.model,
    time:new Date().toLocaleString()
  });
  localStorage.setItem("resumepilot_history",JSON.stringify(h.slice(0,10)));
  renderHistory();
}

function renderHistory(){
  const h=JSON.parse(localStorage.getItem("resumepilot_history")||"[]");
  $("history").innerHTML=h.length?h.map((x,i)=>`
    <div class="history-card" data-i="${i}">
      <div class="history-title">${escapeHtml(x.mode)}</div>
      <div class="history-info">${escapeHtml(x.model)} · ${escapeHtml(x.time)}</div>
      <div class="history-code">${escapeHtml(x.answer.slice(0,150).replace(/\s+/g," "))}</div>
    </div>`).join(""):'<p>No analyses yet.</p>';
  document.querySelectorAll(".history-card").forEach(c=>c.onclick=()=>{
    const x=h[Number(c.dataset.i)];
    latestAnswer=x.answer;
    $("result").innerHTML=markdownLite(x.answer);
    $("meta").textContent=`${x.model} • restored from history`;
    $("copyBtn").disabled=false;$("downloadBtn").disabled=false;
    window.scrollTo({top:0,behavior:"smooth"});
  });
}

$("resumeFile").addEventListener("change",()=>{
  const f=$("resumeFile").files[0];
  $("fileName").textContent=f?`Selected: ${f.name}`:"";
});
$("analyzeBtn").onclick=analyze;
$("clearBtn").onclick=()=>{
  $("resumeFile").value="";$("fileName").textContent="";
  $("resumeText").value="";$("jobDescription").value="";
  $("result").innerHTML='<div class="empty"><div class="empty-icon">✦</div><h3>Your resume analysis will appear here</h3><p>Upload/paste your resume and choose an analysis mode.</p></div>';
  $("meta").textContent="Ready for analysis";latestAnswer="";
  $("copyBtn").disabled=true;$("downloadBtn").disabled=true;
};
$("clearHistory").onclick=()=>{localStorage.removeItem("resumepilot_history");renderHistory();};
$("copyBtn").onclick=async()=>{
  await navigator.clipboard.writeText(latestAnswer);
  $("copyBtn").textContent="Copied!";
  setTimeout(()=>$("copyBtn").textContent="Copy",1200);
};
$("downloadBtn").onclick=()=>{
  const blob=new Blob([latestAnswer],{type:"text/plain;charset=utf-8"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="resume-analysis.txt";a.click();
  URL.revokeObjectURL(a.href);
};
renderHistory();
loadModels();

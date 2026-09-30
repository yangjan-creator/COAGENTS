"use strict";
const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const state = {data:null, templates:[], view:"overview", template:null, drawer:null, fullHistory:null, historyProject:null, actor:"pm", principal:null};
const titles = {overview:"專案總覽",board:"工作看板",versions:"版本與驗證",assets:"檔案與資料資產",timeline:"完整歷程",templates:"Dashboard 模板",members:"團隊與 Agent"};
const statuses = {DRAFT:"草稿",QUEUED:"待開始",CLAIMED:"已認領",WORKING:"進行中",READY_FOR_REVIEW:"待審",VALIDATING:"驗證中",VERIFIED:"已驗證",CLOSED:"已結案",BLOCKED:"阻塞",HOLD:"HOLD",PARKED:"暫停",PENDING:"待驗證",PASSED:"通過",FAILED:"失敗",WAIVED:"豁免",NOT_DECLARED:"未宣告"};
const badge = (value) => '<span class="badge '+esc(value)+'">'+esc(statuses[value] || value)+'</span>';
const date = (value) => value ? new Date(value).toLocaleString("zh-TW",{hour12:false}) : "—";
const size = (value) => {const gb=value/1073741824; return gb>=1 ? gb.toFixed(2)+" GB" : (value/1048576).toFixed(1)+" MB";};
const actor = () => $("actor").value || state.actor;
const toast = (message) => {$("toast").textContent=message;$("toast").hidden=false;setTimeout(()=>{$("toast").hidden=true;},3200);};
async function api(path, method="GET", body=null) {
  const headers={"Content-Type":"application/json"};
  const token=sessionStorage.getItem("coagents-token");
  if(token) headers.Authorization="Bearer "+token;
  const response=await fetch(path,{method,headers,...(body?{body:JSON.stringify(body)}:{})});
  const result=await response.json();
  if(!response.ok) throw new Error(typeof result.detail==="string"?result.detail:JSON.stringify(result.detail));
  return result;
}
const command = (path,body) => api(path,"POST",{actor:actor(),...body});
const options = (rows,selected="") => rows.map((r)=>'<option value="'+esc(r.id)+'" '+(r.id===selected?'selected':'')+'>'+esc(r.name || r.title || r.key)+'</option>').join("");
const field = (name,label,type="text",value="",required=true) => '<label>'+esc(label)+'<input name="'+esc(name)+'" type="'+esc(type)+'" value="'+esc(value)+'" '+(required?'required':'')+'></label>';
const area = (name,label,value="",code=false) => '<label>'+esc(label)+'<textarea name="'+esc(name)+'" '+(code?'class="code"':'')+' required>'+esc(value)+'</textarea></label>';
const select = (name,label,opts,multiple=false,required=true) => '<label>'+esc(label)+'<select name="'+esc(name)+'" '+(multiple?'multiple':required?'required':'')+'>'+opts+'</select></label>';
let saveDialog = null;
function dialog(title,fields,onSave) {
  $("dialog-title").textContent=title;$("dialog-fields").innerHTML=fields;$("dialog-error").textContent="";
  saveDialog=onSave;$("editor").showModal();
}
function closeDialog() {$("editor").close();}
$("cancel").onclick=closeDialog;$("cancel-bottom").onclick=closeDialog;
$("editor-form").onsubmit=async(e)=>{
  e.preventDefault(); const button=e.currentTarget.querySelector('[type="submit"]');button.disabled=true;
  try {await saveDialog(new FormData(e.currentTarget));closeDialog();toast("已儲存，歷程已更新");await load();if(state.drawer)await openItem(state.drawer);}
  catch(error){$("dialog-error").textContent=error.message;}
  finally{button.disabled=false;}
};
function connection() {
  dialog("連線與操作身分",
    '<p class="muted">用管理員 token 或 Agent 自己的 token 連線。Token 僅保存在這個瀏覽器分頁。</p>'+
    field("token","API token（本機開發模式可留空）","password","",false),
    async(form)=>{sessionStorage.setItem("coagents-token",form.get("token")); await load();});
}
$("connect").onclick=connection;
function filteredItems() {
  const team=$("team").value, search=$("search").value.toLowerCase(), project=$("project").value;
  return state.data.items.filter((i)=>(!project||i.project_id===project)&&(!team||i.team_id===team)&&
    [i.key,i.title,i.owner_actor,...i.labels].join(" ").toLowerCase().includes(search));
}
function filtered(key) {
  const project=$("project").value;
  return state.data[key].filter((r)=>!project || r.project_id===project);
}
const panel = (title,body,actions="") => '<section class="panel"><header class="panelhead"><h2>'+esc(title)+'</h2><div class="toolbar">'+actions+'</div></header>'+body+'</section>';
function timeline(events) {
  return '<div class="timeline">'+(events.length?events.map((e)=>'<article class="event"><div class="eventhead"><strong>'+esc(e.actor)+'</strong><span class="badge">'+esc(e.event_type)+'</span></div><p>'+esc(e.message)+'</p><time>'+date(e.created_at)+'</time><details><summary>事件欄位</summary><pre class="mono">'+esc(JSON.stringify(e.payload,null,2))+'</pre></details></article>').join(""):'<p class="empty">還沒有歷程。認領、交付與驗證會自動留下紀錄。</p>')+'</div>';
}
const columns = {key:"編號",title:"工作項目",kind:"類型",owner_actor:"負責人",status:"狀態",version:"交付版本",progress:"進度",team:"團隊",priority:"優先度",validation:"驗證"};
function table(items,cols=["key","title","team","owner_actor","status","version","validation","progress"]) {
  const cells={
    key:(i)=>'<span class="key">'+esc(i.key)+'</span>',
    title:(i)=>'<button class="item-link" data-item="'+esc(i.id)+'">'+esc(i.title)+'</button>',
    kind:(i)=>esc(i.kind),owner_actor:(i)=>esc(i.owner_actor||"待認領"),status:(i)=>badge(i.status),
    version:(i)=>'<span class="mono">'+(i.current_version?'v'+i.current_version.ordinal:'—')+'</span>',
    validation:(i)=>badge(i.validation),
    priority:(i)=>esc(i.priority),team:(i)=>esc(state.data.teams.find(t=>t.id===i.team_id)?.name||"—"),
    progress:(i)=>'<span class="progress"><i><b style="width:'+Number(i.progress_percent)+'%"></b></i>'+Number(i.progress_percent)+'%</span>'
  };
  return '<div class="tablewrap"><table><thead><tr>'+cols.map(c=>'<th>'+esc(columns[c])+'</th>').join("")+'</tr></thead><tbody>'+
    (items.length?items.map(i=>'<tr>'+cols.map(c=>'<td>'+cells[c](i)+'</td>').join("")+'</tr>').join(""):'<tr><td colspan="'+cols.length+'" class="empty">還沒有工作項目。用「開展工作項目」開始。</td></tr>')+'</tbody></table></div>';
}
function board(items) {
  const lanes=[["DRAFT","QUEUED","CLAIMED"],["WORKING"],["READY_FOR_REVIEW","VALIDATING"],["BLOCKED","HOLD","PARKED"],["VERIFIED","CLOSED"]];
  const names=["待開始","進行中","待審與驗證","阻塞與暫停","已驗證與結案"];
  return '<div class="board">'+lanes.map((set,k)=>'<section class="lane"><h3>'+names[k]+' · '+items.filter(i=>set.includes(i.status)).length+'</h3>'+
    items.filter(i=>set.includes(i.status)).map(i=>'<button class="card" data-item="'+esc(i.id)+'"><span class="key">'+esc(i.key)+'</span><p>'+esc(i.title)+'</p>'+badge(i.status)+'<footer><small>'+esc(i.owner_actor||"待認領")+'</small><small>'+(i.current_version?'v'+i.current_version.ordinal:'尚未交付')+'</small></footer></button>').join("")+'</section>').join("")+'</div>';
}
function summaries(entries) {
  return (entries.length?entries.map(s=>'<article class="summary-entry"><strong>'+esc(s.author)+'</strong><small>'+date(s.created_at)+'</small><p>'+esc(s.body_markdown)+'</p><small>'+esc(s.evidence_refs.join(" · "))+'</small></article>').join(""):'<p class="empty">PM 在這裡記下整合判斷與下一步。</p>');
}
function artifacts(entries) {
  return '<div class="tablewrap"><table><thead><tr><th>路徑 / 身分</th><th>大小</th><th>建立者</th><th>用途 / 保留狀態</th><th>引用</th><th>操作</th></tr></thead><tbody>'+
    (entries.length?entries.map(a=>'<tr><td class="assetpath"><span class="mono">'+esc(a.path)+'</span><details><summary>完整 SHA-256</summary><span class="mono">'+esc(a.sha256)+'</span></details></td><td>'+size(a.bytes)+'</td><td>'+esc(a.owner_actor)+'</td><td>'+badge(a.retention_state)+'</td><td>'+a.deletion_check.references.length+'</td><td><button data-check="'+esc(a.id)+'">保留檢查</button></td></tr>').join(""):'<tr><td colspan="6" class="empty">登錄檔案路徑、SHA 與用途。大型資料保留在原位置。</td></tr>')+'</tbody></table></div>';
}
function widget(w,items) {
  let rows=w.query==="blocked"?items.filter(i=>["BLOCKED","HOLD","PARKED"].includes(i.status)):w.query==="verified"?items.filter(i=>["VERIFIED","CLOSED"].includes(i.status)):items;
  if(w.type==="metric") {
    const count=w.query==="pending_gates"?items.reduce((n,i)=>n+i.gates.filter(g=>g.required&&g.status==="PENDING").length,0):rows.length;
    return '<article class="metric '+(w.query==="verified"?'passed':w.query==="blocked"?'blocked':w.query==="pending_gates"?'pending':'')+'"><small>'+esc(w.title)+'</small><strong>'+count+'</strong></article>';
  }
  if(w.type==="table")return panel(w.title,table(rows,w.columns.length?w.columns:undefined));
  if(w.type==="board")return panel(w.title,'<div class="panelbody">'+board(rows)+'</div>');
  if(w.type==="timeline")return panel(w.title,timeline(filtered("events").slice(0,8)));
  if(w.type==="summary")return panel(w.title,summaries(filtered("summaries").slice(0,8)),'<button data-action="summary">＋ 整合紀錄</button>');
  if(w.type==="artifacts")return panel(w.title,artifacts(filtered("artifacts")),'<button data-action="artifact">＋ 登錄檔案</button>');
  throw new Error("不支援的 widget: "+w.type);
}
function render() {
  if(!state.data)return;
  $("error").hidden=true;const items=filteredItems();let html="";
  $("view-label").textContent=titles[state.view];$("heading").textContent=state.view==="overview"?"一起推進，每一步都有紀錄。":titles[state.view];
  document.querySelectorAll("[data-view]").forEach(b=>b.classList.toggle("active",b.dataset.view===state.view));
  if(state.view==="overview") {
    const available=state.templates.filter(t=>(!t.project_id||t.project_id===$("project").value)&&(!t.team_id||t.team_id===$("team").value||!$("team").value));
    const template=available.find(t=>t.id===state.template);
    const layout=template?.revisions.find(r=>r.id===template.current_revision_id)?.layout||state.data.default_layout;
    const chosen=layout.statuses?.length?items.filter(i=>layout.statuses.includes(i.status)):items;
    html='<div class="toolbar" style="margin-bottom:18px"><label>總覽模板 <select id="active-template"><option value="">預設管制總覽</option>'+options(available,state.template||"")+'</select></label><button data-action="overview">編輯專案概況</button></div>';
    const overview=filtered("overviews")[0];
    if($("project").value&&overview)html+=panel("專案概況",'<div class="panelbody overview">'+esc(overview.body_markdown)+'</div>');
    html+='<div class="metrics">'+layout.widgets.filter(w=>w.type==="metric").map(w=>widget(w,chosen)).join("")+'</div>';
    html+=layout.widgets.filter(w=>w.type!=="metric").map(w=>widget(w,chosen)).join("");
  } else if(state.view==="board") html=board(items);
  else if(state.view==="versions") html=panel("交付版本與驗證",table(items,["key","title","version","validation","status","owner_actor"]));
  else if(state.view==="assets")html=panel("檔案與資料資產",artifacts(filtered("artifacts")),'<button data-action="artifact">＋ 登錄檔案</button>');
  else if(state.view==="timeline")html=panel($("project").value?"完整專案歷程":"最新 200 個事件 · 選取專案查看完整歷程",timeline(state.historyProject===$("project").value&&state.fullHistory?state.fullHistory:filtered("events")),'<button data-action="summary">＋ PM Summary</button>');
  else if(state.view==="templates") {
    html=panel("Dashboard 模板",'<div class="panelbody"><p class="muted">調整卡片順序、表格欄位、看板與時間線。每次儲存都保留上一版。</p></div>','<button data-action="template">＋ 新增模板</button>');
    html+=state.templates.map(t=>panel(t.name,'<div class="panelbody"><p>'+esc(t.description)+'</p>'+t.revisions.map(r=>'<details><summary>v'+r.ordinal+' · '+date(r.created_at)+(r.id===t.current_revision_id?' · 目前版本':'')+'</summary><pre>'+esc(JSON.stringify(r.layout,null,2))+'</pre></details>').join("")+'</div>','<button data-template="'+esc(t.id)+'">編輯為下一版</button>')).join("");
  } else if(state.view==="members") {
    html=panel("團隊",'<div class="panelbody">'+state.data.teams.map(t=>'<p><strong>'+esc(t.name)+'</strong> <span class="key">'+esc(t.slug)+'</span></p>').join("")+'</div>','<button data-action="team">＋ 團隊</button>');
    html+=panel("人與 Agent",'<div class="tablewrap"><table><thead><tr><th>成員</th><th>身分</th><th>類型</th><th>角色</th><th>團隊</th><th>API</th></tr></thead><tbody>'+state.data.members.map(m=>'<tr><td>'+esc(m.name)+'</td><td class="mono">'+esc(m.actor)+'</td><td>'+esc(m.kind)+'</td><td>'+esc(m.role)+'</td><td>'+esc(state.data.teams.find(t=>t.id===m.team_id)?.name||"全專案")+'</td><td><button data-member-key="'+esc(m.id)+'">簽發 API key</button></td></tr>').join("")+'</tbody></table></div>','<button data-action="member">＋ 人 / Agent</button>');
  }
  $("content").innerHTML=html;
  if($("active-template"))$("active-template").onchange=e=>{state.template=e.target.value;render();};
}
async function load() {
  try {
    const identity=await api("/session");state.principal=identity.principal;
    const selected=$("project").value, team=$("team").value, oldActor=actor();
    const [data,templates]=await Promise.all([api("/workspace"),api("/dashboard-templates")]);
    state.data=data;state.templates=templates;
    $("project").innerHTML='<option value="">全部專案</option>'+options(data.projects,selected);
    $("team").innerHTML='<option value="">所有團隊</option>'+options(data.teams,team);
    const members=state.principal? [{id:state.principal.actor,name:state.principal.name||"PM 管理員"}] : [{id:"pm",name:"PM 管理員"},...data.members.map(m=>({id:m.actor,name:m.name+" ("+m.actor+")"}))];
    $("actor").innerHTML=options(members,state.principal?.actor||oldActor);if(state.view==="timeline")await loadHistory();else render();
  } catch(error){$("error").hidden=false;$("error").textContent=error.message+"。可在「連線與身分」設定 token。";}
}
async function loadHistory() {
  state.historyProject=$("project").value;
  state.fullHistory=state.historyProject?(await api("/projects/"+state.historyProject+"/history")).reverse():null;
  render();
}
function projectPicker() {return select("project_id","專案",options(state.data.projects,$("project").value));}
function actions(name,id=null) {
  if(!state.data)return;
  if(name==="team")dialog("新增團隊",field("name","團隊名稱")+field("slug","代號"),async(f)=>command("/teams",{name:f.get("name"),slug:f.get("slug")}));
  if(name==="member")dialog("新增人 / Agent",field("name","顯示名稱")+field("member_actor","操作身分（唯一）")+select("kind","類型",'<option>AGENT</option><option>HUMAN</option>')+select("role","角色",'<option>CONTRIBUTOR</option><option>REVIEWER</option><option>PM</option>')+select("team_id","所屬團隊",options(state.data.teams)),async(f)=>command("/members",Object.fromEntries(f)));
  if(name==="project") {
    if(!state.data.teams.length){actions("team");return;}
    dialog("新增共同專案",field("key","專案代號")+field("name","專案名稱")+select("team_id","主要團隊",options(state.data.teams))+select("team_ids","共同參與團隊（可多選）",options(state.data.teams),true),async(f)=>command("/projects",{key:f.get("key"),name:f.get("name"),team_id:f.get("team_id"),team_ids:f.getAll("team_ids")}));
  }
  if(name==="item") {
    if(!state.data.projects.length){actions("project");return;}
    dialog("開展工作項目",projectPicker()+field("key","項目編號，例如 BAD-001")+field("title","工作名稱")+select("kind","類型",'<option value="TASK">任務</option><option value="FEATURE">功能</option><option value="SUBPROJECT">子專案</option>')+select("team_id","執行團隊",options(state.data.teams))+select("parent_id","上層項目",'<option value="">無</option>'+options(state.data.items),false,false)+select("priority","優先度",'<option>NORMAL</option><option>HIGH</option><option>URGENT</option><option>LOW</option>')+area("description","範圍與完成條件"),async(f)=>command("/projects/"+f.get("project_id")+"/items",{key:f.get("key"),title:f.get("title"),kind:f.get("kind"),team_id:f.get("team_id"),parent_id:f.get("parent_id")||null,priority:f.get("priority"),description:f.get("description")}));
  }
  if(name==="summary"||name==="overview") {
    if(!state.data.projects.length){actions("project");return;}
    const existing=name==="overview"?filtered("overviews")[0]?.body_markdown||"":"";
    dialog(name==="summary"?"新增 PM 整合紀錄":"編輯專案概況",projectPicker()+area("body_markdown",name==="summary"?"目前判斷、阻點、下一步":"目標、完成定義與目前狀態",existing)+(name==="summary"?field("refs","證據路徑或 ID（以逗號分隔）","text","",false):""),async(f)=>command("/projects/"+f.get("project_id")+"/"+(name==="summary"?"pm-summaries":"overview"),{body_markdown:f.get("body_markdown"),...(name==="summary"?{evidence_refs:f.get("refs").split(",").map(v=>v.trim()).filter(Boolean)}:{})}));
  }
  if(name==="artifact") {
    if(!state.data.projects.length){actions("project");return;}
    dialog("登錄檔案與資料資產",projectPicker()+field("path","原始絕對路徑")+field("sha256","完整 SHA-256")+field("bytes","大小（bytes）","number")+field("media_type","檔案類型","text","application/json")+select("purpose","保留用途",'<option>EVIDENCE</option><option>UNIQUE_INPUT</option><option>ROLLBACK_POINT</option><option>VERIFIED_EPHEMERAL</option>')+field("source_ref","來源（選填）","text","",false),async(f)=>command("/projects/"+f.get("project_id")+"/artifacts",{path:f.get("path"),sha256:f.get("sha256"),bytes:Number(f.get("bytes")),media_type:f.get("media_type"),purpose:f.get("purpose"),source_ref:f.get("source_ref")||null}));
  }
  if(name==="template") {
    const t=state.templates.find(t=>t.id===id), layout=t?.revisions.find(r=>r.id===t.current_revision_id)?.layout||state.data.default_layout;
    dialog(t?"模板：建立下一版":"新增 Dashboard 模板",(t?"":field("name","模板名稱"))+area("layout","Template JSON（卡片、欄位、順序、篩選）",JSON.stringify(layout,null,2),true),async(f)=>command(t?"/dashboard-templates/"+t.id+"/revisions":"/dashboard-templates",{...(t?{}:{name:f.get("name")}),layout:JSON.parse(f.get("layout"))}));
  }
}
async function openItem(id) {
  try {
    state.drawer=id; const h=await api("/items/"+id+"/history"), i=h.item;
    const project=state.data.projects.find(p=>p.id===i.project_id);
    const gates=(v)=>h.gates[v.id].map(g=>'<div class="gate '+esc(g.status)+'"><strong>'+esc(g.name)+'</strong> '+badge(g.status)+' <small>'+(g.required?'必須通過':'選用')+'</small>'+
      (g.evidence_uri?'<p class="mono">'+esc(g.evidence_uri)+'</p><details><summary>完整 SHA-256</summary><span class="mono">'+esc(g.evidence_sha256)+'</span></details><small>'+esc(g.checked_by)+' · '+date(g.checked_at)+'</small>':'')+
      (g.status==="PENDING"?'<div class="toolbar"><button data-gate-result="'+esc(g.id)+'">記錄驗證結果</button></div>':'')+'</div>').join("");
    $("drawer-content").innerHTML='<p class="eyebrow">'+esc(project?.key)+' / '+esc(i.key)+'</p><h2>'+esc(i.title)+'</h2>'+badge(i.status)+' '+badge(i.validation)+
      '<p class="description">'+esc(i.description)+'</p><div class="detailrow"><span class="key">負責人</span>'+esc(i.owner_actor||"待認領")+'</div>'+
      '<div class="detailrow"><span class="key">進度</span>'+i.progress_percent+'%</div>'+
      (i.parent_id?'<div class="detailrow"><span class="key">上層</span><button data-item="'+esc(i.parent_id)+'">開啟上層項目</button></div>':'')+
      '<div class="toolbar"><button data-edit="'+esc(i.id)+'">編輯內容</button><button data-claim="'+esc(i.id)+'">認領</button><button data-progress="'+esc(i.id)+'">回報進度</button><button data-version="'+esc(i.id)+'">＋ 交付版本</button><button data-dependency="'+esc(i.id)+'">＋ 依賴</button><button data-close="'+esc(i.id)+'">結案</button></div>'+
      '<h3 style="margin-top:25px">版本與驗證</h3><div class="versionstrip">'+h.versions.map(v=>'<span class="'+(v.id===i.current_version_id?'current':'')+'">v'+v.ordinal+' · '+esc(statuses[v.state]||v.state)+'</span>').join("")+'</div>'+
      (h.versions.length?h.versions.slice().reverse().map(v=>'<section class="versionbox"><h3>v'+v.ordinal+' '+(v.id===i.current_version_id?'· 目前交付':'')+'</h3><p>'+esc(v.change_note)+'</p><p class="mono">'+esc(v.source_ref||"尚未綁 Git / 交付檔")+'</p>'+(v.source_sha256?'<details><summary>交付 SHA-256</summary><span class="mono">'+esc(v.source_sha256)+'</span></details>':'')+'<small>'+esc(v.created_by)+' · '+date(v.created_at)+'</small>'+gates(v)+(v.state!=="VERIFIED"&&v.state!=="FAILED"?'<div class="toolbar"><button data-gate="'+esc(v.id)+'">＋ 宣告驗證格</button></div>':'')+'</section>').join(""):'<p class="empty">交付 v1 後，驗證格與證據會列在這裡。</p>')+
      '<h3 style="margin:20px 0">引用檔案</h3>'+state.data.artifacts.filter(a=>a.deletion_check.references.some(r=>h.versions.some(v=>v.id===r.ref_id)||Object.values(h.gates).flat().some(g=>g.id===r.ref_id))).map(a=>'<p class="mono">'+esc(a.path)+'</p>').join("")+
      '<h3 style="margin-top:20px">項目完整歷程</h3>'+timeline(h.events.slice().reverse());
    $("drawer").hidden=false;
  }catch(error){$("error").hidden=false;$("error").textContent=error.message;}
}
$("close-drawer").onclick=()=>{$("drawer").hidden=true;state.drawer=null;};
document.addEventListener("click",async(e)=>{
  const b=e.target.closest("button");if(!b)return;
  try {
    if(b.dataset.view){state.view=b.dataset.view;if(state.view==="timeline")await loadHistory();else render();}
    if(b.dataset.item)await openItem(b.dataset.item);
    if(b.dataset.action)actions(b.dataset.action);
    if(b.dataset.template)actions("template",b.dataset.template);
    if(b.dataset.edit){const i=state.data.items.find(i=>i.id===b.dataset.edit);dialog("編輯工作內容",field("title","工作名稱","text",i.title)+area("description","範圍與完成條件",i.description)+field("labels","標籤（逗號分隔）","text",i.labels.join(","),false),async(f)=>api("/items/"+i.id,"PATCH",{actor:actor(),title:f.get("title"),description:f.get("description"),labels:f.get("labels").split(",").map(v=>v.trim()).filter(Boolean)}));}
    if(b.dataset.claim){await command("/items/"+b.dataset.claim+"/claim",{});toast("認領成功");await load();await openItem(b.dataset.claim);}
    if(b.dataset.close){await command("/items/"+b.dataset.close+"/close",{});await load();await openItem(b.dataset.close);}
    if(b.dataset.progress)dialog("回報進度",select("status","狀態",["WORKING","READY_FOR_REVIEW","VALIDATING","BLOCKED","HOLD","PARKED"].map(s=>'<option value="'+s+'">'+statuses[s]+'</option>').join(""))+field("progress_percent","進度百分比","number","0")+area("message","已完成什麼、下一步或阻塞原因"),async(f)=>command("/items/"+b.dataset.progress+"/progress",{status:f.get("status"),progress_percent:Number(f.get("progress_percent")),message:f.get("message")}));
    if(b.dataset.version)dialog("新增交付版本",area("change_note","本版改動與交付內容")+field("source_ref","Git commit / PR / 交付檔路徑","text","",false)+field("source_sha256","完整 SHA-256（選填）","text","",false),async(f)=>command("/items/"+b.dataset.version+"/versions",{change_note:f.get("change_note"),source_ref:f.get("source_ref")||null,source_sha256:f.get("source_sha256")||null}));
    if(b.dataset.gate)dialog("宣告驗證格",field("name","要驗證的性質")+select("required","是否必要",'<option value="true">必須通過</option><option value="false">選用</option>'),async(f)=>command("/versions/"+b.dataset.gate+"/gates",{name:f.get("name"),required:f.get("required")==="true"}));
    if(b.dataset.gateResult)dialog("記錄驗證結果",select("status","結果",'<option value="PASSED">通過</option><option value="FAILED">失敗</option><option value="WAIVED">PM 豁免</option>')+field("evidence_uri","證據檔案路徑 / URI")+field("evidence_sha256","證據完整 SHA-256")+area("message","量法、结果或豁免理由"),async(f)=>command("/gates/"+b.dataset.gateResult+"/result",Object.fromEntries(f)));
    if(b.dataset.dependency)dialog("新增依賴",select("depends_on_id","等待哪個項目",options(state.data.items.filter(i=>i.id!==b.dataset.dependency))),async(f)=>command("/items/"+b.dataset.dependency+"/dependencies",{depends_on_id:f.get("depends_on_id")}));
    if(b.dataset.check){const c=await api("/artifacts/"+b.dataset.check+"/deletion-check");dialog("保留檢查",'<p><strong>'+esc(c.allowed?"登錄上無保護或引用":"目前必須保留")+'</strong></p><p class="mono">'+esc(c.path)+'</p><p>'+esc(c.reason)+'</p><p class="muted">此結果只核登錄紀錄。實體刪除前仍須確認程序占用、唯一輸入與回滾用途。</p><pre class="mono">'+esc(JSON.stringify(c.references,null,2))+'</pre>',async()=>{});}
    if(b.dataset.memberKey){const result=await command("/members/"+b.dataset.memberKey+"/keys",{});dialog("保存新 API key",'<p class="muted">完整 key 只顯示這一次。請存到你的秘密設定。</p>'+area("token","API key",result.token,true),async()=>{});}
  }catch(error){$("error").hidden=false;$("error").textContent=error.message;}
});
$("new-project").onclick=()=>actions("project");$("new-item").onclick=()=>actions("item");
$("refresh").onclick=load;$("project").onchange=async()=>{try{if(state.view==="timeline")await loadHistory();else render();}catch(error){$("error").hidden=false;$("error").textContent=error.message;}};$("team").onchange=render;$("search").oninput=render;
$("actor").onchange=()=>{state.actor=actor();};
load();


const $=s=>document.querySelector(s), $$=s=>document.querySelectorAll(s);
let source="file";
$$(".tab").forEach(b=>b.onclick=()=>{source=b.dataset.tab;$$(".tab").forEach(x=>x.classList.toggle("active",x===b));$("#filePanel").classList.toggle("hidden",source!=="file");$("#youtubePanel").classList.toggle("hidden",source!=="youtube")});
$("#video").onchange=()=>$("#fileName").textContent=$("#video").files[0]?.name||"Nenhum arquivo selecionado";
$("#again").onclick=()=>location.reload();
$("#form").onsubmit=async e=>{
 e.preventDefault(); const go=$("#go");go.disabled=true;$("#progress").classList.remove("hidden");$("#results").classList.add("hidden");
 const fd=new FormData($("#form"));fd.set("source_type",source);if(source==="youtube"){fd.delete("video")}
 try{
  const r=await fetch("/api/process",{method:"POST",body:fd});const data=await r.json();if(!r.ok)throw Error(data.error||"Erro");
  poll(data.job_id);
 }catch(err){alert(err.message);go.disabled=false}
};
async function poll(id){
 const r=await fetch("/api/job/"+id);const j=await r.json();
 $("#bar").style.width=(j.progress||0)+"%";$("#pct").textContent=(j.progress||0)+"%";$("#status").textContent=j.message||"Processando...";
 if(j.status==="done"){render(j.clips||[]);$("#go").disabled=false;return}
 if(j.status==="error"){alert(j.message||"Erro");$("#go").disabled=false;return}
 setTimeout(()=>poll(id),1200);
}
function render(clips){$("#clips").innerHTML="";clips.forEach((c,i)=>{const el=document.createElement("article");el.className="clip";el.innerHTML=`<video controls playsinline preload="metadata" src="${c.url}"></video><strong>Corte ${String(i+1).padStart(2,"0")}</strong><small>${c.start}s • ${c.duration}s</small><a class="download" href="${c.download}">⬇ Baixar MP4</a>`;$("#clips").appendChild(el)});$("#results").classList.remove("hidden");$("#results").scrollIntoView({behavior:"smooth"})}

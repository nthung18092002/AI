const $ = s => document.querySelector(s);
const form = $('#form'), button = $('#submit');
let active = null, polling = false, project = null, sequence = false;
const hints = {
  reference: 'FLUX.2 Klein 4B dựng khung từ ảnh sản phẩm và khung đầu làm tham chiếu người/bối cảnh. I2V dùng model bạn chọn bên dưới. Chưa kiểm chứng chất lượng/VRAM trên RTX 5070 12GB.',
  wan: 'Chế độ cũ Wan 2.1 T2V 1.3B: không nhận ảnh điều kiện, dễ đổi người/bối cảnh/sản phẩm. Không phù hợp cho yêu cầu giữ đúng bao bì.',
  sdxl: 'Chế độ ảnh AI từ text rồi zoom. Ảnh sản phẩm không phải điều kiện của model này; dùng chế độ tham chiếu để đưa ảnh vào model.',
  photos: 'Dựng trực tiếp ảnh thật, không sinh người hoặc động tác bằng AI. Giữ nguyên hình ảnh sản phẩm.',
  comfy: 'Workflow riêng với các node local trong danh sách hỗ trợ. Chưa tự động ánh xạ ảnh vào graph; dùng luồng tham chiếu nếu cần ảnh điều kiện.'
};
const safeKeys = ['product','prompt','features','cta','duration','quality','video_backend','mode','speech','use_ollama','auto_music','burn_subtitles','speech_delivery','ollama_model','comfy_url','voice','seed'];
function settings() {
  const data = Object.fromEntries(new FormData(form));
  for (const key of ['use_ollama','auto_music','burn_subtitles']) data[key] = form.elements[key].checked;
  return data;
}
function modeHelp() {
  const reference = form.elements.mode.value === 'reference';
  $('#mode-help').textContent = hints[form.elements.mode.value];
  $('#custom').hidden = form.elements.mode.value !== 'comfy';
  $('#images').multiple = !reference;
  $('#video-model').hidden = !reference;
  $('#video-model-help').textContent = form.elements.video_backend.value === 'wan22_a14b'
    ? 'A14B là nhánh model lớn hơn, bản GGUF Q4 giảm bộ nhớ trọng số. Cài setup-windows.bat -Profile reference-hq (ít nhất 70GB trống), đóng/mở lại tool. Chưa benchmark trên 12GB VRAM/32GB RAM; offload có thể rất chậm hoặc thiếu bộ nhớ. Thử clip ngắn trước.'
    : '5B nhẹ hơn A14B; cài profile reference. I2V vẫn có thể biến dạng hoặc đổi người. Chưa có kết quả benchmark RTX 5070.';
  button.textContent = reference ? '✦ Chuẩn bị khung cảnh tham chiếu' : 'Tạo video theo chế độ đã chọn';
}
try {
  const saved = JSON.parse(localStorage.getItem('studio-settings') || '{}');
  if (localStorage.getItem('studio-settings-version') !== 'reference-v1') {
    saved.mode = 'reference'; saved.burn_subtitles = false; saved.speech_delivery = 'as_requested';
    localStorage.setItem('studio-settings-version', 'reference-v1');
  }
  for (const key of safeKeys) if (saved[key] !== undefined) {
    const element = form.elements[key];
    if (element.type === 'checkbox') element.checked = saved[key]; else element.value = saved[key];
  }
} catch {}
form.onchange = () => { modeHelp(); try { localStorage.setItem('studio-settings', JSON.stringify(settings())); } catch {} };
modeHelp();
$('#images').addEventListener('change', () => {
  const area = $('#thumbnails');
  for (const image of area.children) URL.revokeObjectURL(image.src);
  area.replaceChildren();
  for (const file of [...$('#images').files].slice(0,12)) {
    const image = new Image(); image.src = URL.createObjectURL(file); image.alt = file.name; area.append(image);
  }
});
async function api(url, options) {
  const response = await fetch(url, options), data = await response.json();
  if (!response.ok) throw Error(data.error || 'Không kết nối được ứng dụng local.');
  return data;
}
function post(url, data) { return api(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
function text(tag, content) { const element = document.createElement(tag); element.textContent = content; return element; }
function setBusy(value) {
  button.disabled = value;
  for (const selector of ['#approve-frames','#preview-scenes','#approve-motion','#export-reference','#project-delivery']) $(selector).disabled = value;
  if (!value && project) projectControls();
}
async function health() {
  $('#refresh').disabled = true;
  try {
    const state = await api('/api/system'), area = $('#health'); area.replaceChildren();
    const required = ['flux-2-klein-4b-fp8.safetensors','qwen_3_4b.safetensors','flux2-vae.safetensors','umt5_xxl_fp8_e4m3fn_scaled.safetensors'];
    const installed = names => names.every(name=>state.installed_assets?.includes(name));
    const checks = [['FFmpeg',state.ffmpeg],['Ollama',state.ollama && state.ollama_models?.length],['ComfyUI',state.comfy],['Ảnh tham chiếu',installed(required)],['Wan 5B',installed(['wan2.2_ti2v_5B_fp16.safetensors','wan2.2_vae.safetensors'])],['Wan A14B Q4',state.gguf_loader_installed && installed(['Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf','Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf','wan_2.1_vae.safetensors'])],['Piper',state.piper],['eSpeak',state.espeak],['MuseTalk cấu hình',state.lipsync?.configured]];
    for (const [label, okay] of checks) { const chip = text('span',(okay?'● ':'○ ')+label); chip.className='chip '+(okay?'ok':'warn'); area.append(chip); }
    $('#system-detail').textContent = JSON.stringify(state,null,2);
  } catch(error) { $('#health').textContent = error.message; }
  finally { $('#refresh').disabled=false; }
}
$('#refresh').onclick=health; health();
async function showResult(job) {
  $('#result').hidden=false; $('#result video').src=job.video;
  const links=$('#links'); links.replaceChildren();
  for (const [label,url] of [['Tải MP4',job.video],['Phụ đề SRT',job.subtitles],['Kịch bản JSON',job.storyboard]]) {
    const link=text('a',label); link.href=url+'?download=1'; link.download=''; links.append(link);
  }
  try { const story=await api(job.storyboard); const lines=story.lines || story.plan?.lines || []; $('#script').textContent=lines.map((line,index)=>`${index+1}. ${line}`).join('\n\n'); }
  catch { $('#script').textContent='Không đọc được kịch bản.'; }
}
function checkbox(label, className, index, checked=false) {
  const wrapper=text('label',''); wrapper.className='check';
  const input=document.createElement('input'); input.type='checkbox'; input.className=className; input.dataset.index=index; input.checked=checked; input.onchange=projectControls;
  wrapper.append(input,document.createTextNode(label)); return wrapper;
}
function projectControls() {
  if (!project || polling || sequence) return;
  const allFrames=[...document.querySelectorAll('.frame-review')].every(el=>el.checked);
  const allMotion=project.previews.length===project.frames.length && [...document.querySelectorAll('.motion-review')].every(el=>el.checked);
  $('#approve-frames').disabled=!allFrames;
  $('#preview-scenes').disabled=!project.frames_approved;
  $('#approve-motion').disabled=!allMotion;
  const approvedMotion=project.previews.length===project.frames.length && project.previews.every(clip=>clip.approved);
  const blocked=project.plan.requires_lipsync && !project.lipsync.configured;
  $('#export-reference').disabled=!(project.frames_approved && approvedMotion) || blocked;
  $('#project-delivery').disabled=false;
  $('#export-requirement').textContent=blocked ? 'Prompt yêu cầu khớp môi. Chưa có MuseTalk local: bản xuất đầy đủ bị chặn. Clip thử chỉ kiểm tra hình. Cài module theo docs/REFERENCE.md hoặc chủ động đổi sang lồng tiếng nếu bạn chấp nhận thay yêu cầu.' : (project.plan.requires_lipsync ? 'Bản xuất sẽ gọi MuseTalk local cho từng cảnh. Cấu hình tồn tại chưa chứng minh chất lượng/khả năng chạy GPU; lỗi sẽ dừng, không fallback voiceover.' : 'Bản xuất dùng lồng tiếng, không có bước đồng bộ môi.');
}
function showProject(data) {
  project=data; $('#reference-review').hidden=false;
  $('#reference-state').textContent=`${data.plan.duration} giây · ${data.video_backend === 'wan22_a14b' ? 'A14B Q4' : '5B'} · ${data.state}`;
  $('#reference-warnings').textContent=data.warnings.join('\n');
  $('#project-delivery').value=data.speech_delivery || 'as_requested';
  const frames=$('#reference-frames'); frames.replaceChildren();
  for (const frame of data.frames) {
    const card=text('article',''); card.append(text('h3',`Cảnh ${frame.index+1} · ${frame.start}–${frame.end}s`));
    const link=document.createElement('a'); link.href=frame.image; link.target='_blank'; link.rel='noopener';
    const image=document.createElement('img'); image.src=frame.image; image.alt=`Khung cảnh ${frame.index+1} cần kiểm tra`; link.append(image); card.append(link,text('p',frame.dialogue));
    if(frame.voice) { const audio=document.createElement('audio'); audio.src=frame.voice; audio.controls=true; card.append(audio); }
    card.append(checkbox('Đã kiểm tra bao bì, người, bối cảnh','frame-review',frame.index,data.frames_approved)); frames.append(card);
  }
  const previews=$('#reference-previews'); previews.replaceChildren();
  for (const clip of data.previews) {
    const card=text('article',''); card.append(text('h3',`Thử chuyển động cảnh ${clip.index+1}`));
    const video=document.createElement('video'); video.src=clip.video; video.controls=true; video.preload='metadata'; card.append(video,text('small','Clip thử chỉ kiểm tra hình, chưa đồng bộ môi.'));
    card.append(checkbox('Mặt, tay và bao bì chấp nhận được','motion-review',clip.index,clip.approved)); previews.append(card);
  }
  projectControls();
}
async function referenceJob(action, extra={}) {
  const result=await post('/api/reference/'+action,{project_id:project.project_id,...extra});
  return watch(result.id);
}
$('#approve-frames').onclick=async()=>{try{showProject(await post('/api/reference/approve',{project_id:project.project_id,frame_hashes:project.frames.map(frame=>frame.sha256)}));}catch(error){$('#reference-warnings').textContent=error.message;}};
$('#preview-scenes').onclick=async()=>{
  sequence=true;setBusy(true);
  try { const id=project.project_id; for (const frame of project.frames) { const job=await post('/api/reference/preview',{project_id:id,scene_index:frame.index}); await watch(job.id); } }
  catch(error){$('#status').textContent=error.message;}
  finally{sequence=false;setBusy(false);}
};
$('#approve-motion').onclick=async()=>{try{for(const clip of project.previews){await post('/api/reference/approve-motion',{project_id:project.project_id,scene_index:clip.index,preview_sha256:clip.sha256});}showProject(await api('/api/reference/'+project.project_id));}catch(error){$('#reference-warnings').textContent=error.message;}};
$('#project-delivery').onchange=async()=>{try{showProject(await post('/api/reference/delivery',{project_id:project.project_id,speech_delivery:$('#project-delivery').value}));}catch(error){$('#reference-warnings').textContent=error.message;}};
$('#export-reference').onclick=async()=>{try{await referenceJob('export');}catch(error){$('#status').textContent=error.message;}};
async function history() {
  try {
    const list=await api('/api/jobs'), area=$('#history'); area.replaceChildren();
    if(!list.length) area.textContent='Chưa có tác vụ.';
    for(const job of list) {
      const row=text('div','');row.className='history-item';row.append(text('span',job.title),text('small',({done:'Hoàn tất bước',running:'Đang chạy',error:'Lỗi',cancelled:'Đã hủy',interrupted:'Gián đoạn'})[job.status]||job.status));
      if(job.status==='done') {
        const view=text('button',job.kind==='reference'?'Mở dự án':'Xem');view.type='button';view.className='secondary';
        view.onclick=async()=>{try{if(job.kind==='reference')showProject(await api('/api/reference/'+job.project_id));else await showResult(job);}catch(error){$('#status').textContent=error.message;}};row.append(view);
      } else if(job.status==='running'&&!polling&&!sequence) watch(job.id).catch(()=>{});
      if(job.error) row.title=job.error;area.append(row);
    }
  } catch(error){$('#history').textContent=error.message;}
}
$('#history-refresh').onclick=history;history();
async function watch(id) {
  active=id;polling=true;setBusy(true);$('#job-panel').hidden=false;$('#job-panel progress').hidden=false;$('#cancel').disabled=false;
  try {
    while(true) {
      const job=await api('/api/jobs/'+id);$('#status').textContent=job.message||job.error||'Đang xử lý…';
      if(job.status==='done') { if(job.kind==='reference')showProject(job);else await showResult(job);$('#status').textContent='Hoàn tất bước. Kiểm tra kết quả trước khi tiếp tục.';return job; }
      if(job.status!=='running')throw Error(job.error||'Tác vụ đã dừng.');
      await new Promise(resolve=>setTimeout(resolve,1200));
    }
  } catch(error){$('#status').textContent=error.message;throw error;}
  finally{active=null;polling=false;$('#cancel').disabled=true;$('#job-panel progress').hidden=true;if(!sequence)setBusy(false);history();}
}
$('#cancel').onclick=async()=>{if(!active)return;$('#cancel').disabled=true;try{await post('/api/jobs/'+active+'/cancel',{});$('#status').textContent='Đang hủy; chờ bước hiện tại dừng…';}catch(error){$('#status').textContent=error.message;$('#cancel').disabled=false;}};
async function encode(file) { if(!file)return null;return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);}); }
form.onsubmit=async event=>{
  event.preventDefault();setBusy(true);$('#job-panel').hidden=false;$('#job-panel progress').hidden=false;$('#result').hidden=true;$('#status').textContent='Đang chuẩn bị…';
  try {
    const files=[...$('#images').files];for(const key of ['narration','music'])if($('#'+key).files[0])files.push($('#'+key).files[0]);
    if(files.reduce((sum,file)=>sum+file.size,0)>70*1024*1024)throw Error('Tổng file tối đa 70MB trước khi mã hóa.');
    const data=settings();data.images=await Promise.all([...$('#images').files].map(encode));
    for(const key of ['narration','music'])data[key]=await encode($('#'+key).files[0]);
    const workflow=$('#workflow').files[0];if(data.mode==='comfy'&&workflow)data.workflow=JSON.parse(await workflow.text());
    const job=await post(data.mode==='reference'?'/api/reference/prepare':'/api/render',data);await watch(job.id);
  } catch(error){$('#status').textContent=error.message;}
  finally{if(!sequence)setBusy(false);$('#job-panel progress').hidden=true;}
};

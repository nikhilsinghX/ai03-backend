(() => {
  const $ = id => document.getElementById(id);
  const state = { session: null, rubric: null, plan: null, busy: false, currentTurn: null, transcript: [], assessment: null, reviewerDecision: null, recognition: null, listening: false };
  const SAMPLE_JD = `AI/ML Intern\nResponsibilities: build Python data pipelines, experiment with machine-learning models, evaluate results, explain technical choices, and collaborate with engineers.\nRequirements: Python, ML fundamentals, problem-solving, project ownership, clear technical communication, and willingness to learn.`;
  const SAMPLE_RESUME = `Fictional Candidate — AI/ML Intern\nBuilt a small Python document-search prototype using embeddings and retrieval. Wrote a data-cleaning script and compared retrieval results on a small held-out set. Worked with two classmates, reviewed feedback, and improved the evaluation notebook. Familiar with Python, pandas, APIs, and introductory machine learning.`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function toast(message, type='info') { const el=$('toast'); el.textContent=message; el.className=`toast toast-${type}`; window.clearTimeout(toast.timer); toast.timer=window.setTimeout(()=>el.classList.add('hidden'),5000); }
  function show(view) {
    document.querySelectorAll('main section[id^="view-"]').forEach(el => el.classList.add('hidden'));
    $(`view-${view}`).classList.remove('hidden');
    document.querySelectorAll('.step').forEach(el => { const order=['setup','rubric','consent','interview','report']; el.classList.toggle('active', order.indexOf(el.dataset.step) <= order.indexOf(view)); el.classList.toggle('current', el.dataset.step === view); });
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function setBusy(on, message='Working…') { state.busy=on; $('generateBtn').disabled=on; $('generateBtn').innerHTML=on ? `<span class="spinner"></span> ${esc(message)}` : 'Generate rubric &amp; questions <span aria-hidden="true">→</span>'; }
  async function checkHealth() {
    try { const h=await InterviewAPI.health(); $('apiStatus').textContent=h.mock_llm ? 'Backend online · Demo mode' : 'Backend online · LLM enabled'; $('apiStatus').previousElementSibling.classList.add('live-dot'); }
    catch { $('apiStatus').textContent='Backend offline · start FastAPI on port 8000'; $('apiStatus').previousElementSibling.classList.add('offline-dot'); }
  }
  function renderRubric() {
    const criteria=state.rubric.criteria || [];
    $('criteriaCount').textContent=`${criteria.length} criteria`;
    $('rubricBox').innerHTML=criteria.map((c,i)=>`<article class="criterion-card"><div class="criterion-top"><span class="criterion-number">${String(i+1).padStart(2,'0')}</span><label class="field compact grow"><span>Criterion name</span><input data-criterion="${esc(c.id)}" data-key="name" value="${esc(c.name)}" maxlength="90"></label><label class="field compact weight-field"><span>Weight</span><input data-criterion="${esc(c.id)}" data-key="weight" type="number" min="0" max="100" step="1" value="${esc(c.weight ?? 1)}"></label></div><label class="field compact"><span>What this measures</span><textarea data-criterion="${esc(c.id)}" data-key="description" rows="2">${esc(c.description || c.what_good_looks_like || '')}</textarea></label><div class="anchors"><label class="field compact"><span>1 · Needs development</span><textarea data-criterion="${esc(c.id)}" data-anchor="1" rows="2">${esc(c.anchors?.['1'] || '')}</textarea></label><label class="field compact"><span>3 · Meets expectations</span><textarea data-criterion="${esc(c.id)}" data-anchor="3" rows="2">${esc(c.anchors?.['3'] || '')}</textarea></label><label class="field compact"><span>5 · Strong evidence</span><textarea data-criterion="${esc(c.id)}" data-anchor="5" rows="2">${esc(c.anchors?.['5'] || '')}</textarea></label></div></article>`).join('');
    $('questionCount').textContent=`${state.plan.length} questions`;
    $('questionBox').innerHTML=state.plan.map((q,i)=>`<article class="question-card"><span class="question-index">Q${String(i+1).padStart(2,'0')}</span><div class="question-content"><p>${esc(q.text)}</p><div class="tags"><span class="tag">${esc(criteria.find(c=>c.id===q.criterion_id)?.name || q.criterion_id)}</span><span class="tag tag-source">Source: ${esc(q.source?.type || 'job-related')} · ${esc(q.source?.ref || 'role requirements / résumé')}</span></div></div></article>`).join('');
  }
  function collectRubric() {
    const updated=structuredClone(state.rubric);
    document.querySelectorAll('[data-criterion][data-key]').forEach(el=>{
      const c=updated.criteria.find(x=>x.id===el.dataset.criterion); if(!c) return;
      if(el.dataset.key==='weight') c.weight=Number(el.value)||0; else if(el.dataset.key==='description') c.description=el.value.trim(); else c[el.dataset.key]=el.value.trim();
    });
    document.querySelectorAll('[data-criterion][data-anchor]').forEach(el=>{const c=updated.criteria.find(x=>x.id===el.dataset.criterion); if(c) c.anchors[el.dataset.anchor]=el.value.trim();});
    if(updated.criteria.some(c=>!c.name || !c.description || ['1','3','5'].some(k=>!c.anchors?.[k]))) throw new Error('Please complete each criterion and all three score anchors.');
    const total=updated.criteria.reduce((n,c)=>n+Math.max(0,c.weight),0); if(total<=0) throw new Error('At least one criterion must have a positive weight.');
    // Store weights as percentages for easier reading in the report.
    updated.criteria.forEach(c=>c.weight=Math.round(c.weight*100/total));
    return updated;
  }
  function wireUpload(inputId,targetId){const el=$(inputId); if(!el) return; el.addEventListener('change',()=>{const f=el.files[0]; if(!f) return; if(!/\.(txt|md)$/i.test(f.name)){toast('Please upload a .txt or .md file, or paste the text.','error');el.value='';return;} const r=new FileReader(); r.onload=()=>{$(targetId).value=String(r.result||'').slice(0,20000); $('setupStatus').textContent=`Loaded ${f.name}.`;}; r.readAsText(f);});}
  wireUpload('jdFile','jd'); wireUpload('resumeFile','resume');
  $('loadSample').addEventListener('click',()=>{ $('jd').value=SAMPLE_JD; $('resume').value=SAMPLE_RESUME; $('setupStatus').textContent='Fictional sample data loaded.'; });
  $('generateBtn').addEventListener('click',async()=>{
    const jd=$('jd').value.trim(), resume=$('resume').value.trim();
    if(!jd||!resume){toast('Add both the job description and résumé, or load the sample data.','error');return;}
    setBusy(true,'Generating rubric…'); $('setupStatus').textContent='Creating session and generating job-related criteria…';
    try {
      state.session=await InterviewAPI.createSession(jd,resume);
      state.rubric=state.session.rubric;
      state.plan=(state.session.questions&&state.session.questions.length)?state.session.questions:Object.entries(state.session.plan||{}).map(([criterion_id,text])=>({criterion_id,text,source:{type:'resume',ref:'Candidate résumé'}}));
      if(!state.rubric || !state.plan.length) throw new Error('The backend returned an empty rubric or question plan.');
      renderRubric(); $('setupStatus').textContent='Rubric generated. Review and edit before continuing.'; show('rubric');
    } catch(e) { $('setupStatus').textContent=e.message; toast(e.message,'error'); }
    finally { setBusy(false); }
  });
  $('rubricBox').addEventListener('change',()=>{});
  $('backToSetup').addEventListener('click',()=>show('setup'));
  $('toConsent').addEventListener('click',async()=>{
    try { state.rubric=collectRubric(); $('toConsent').disabled=true; await InterviewAPI.editRubric(state.session.id,state.rubric); renderRubric(); $('consentBox').checked=false; $('startInterview').disabled=true; $('consentStatus').textContent='Consent has not been recorded.'; show('consent'); }
    catch(e){toast(e.message,'error');} finally {$('toConsent').disabled=false;}
  });
  $('backToRubric').addEventListener('click',()=>show('rubric'));
  $('consentBox').addEventListener('change',e=>{$('startInterview').disabled=!e.target.checked; $('consentStatus').textContent=e.target.checked?'Consent checkbox selected. Click the button to record it.':'Consent has not been recorded.';});
  $('startInterview').addEventListener('click',async()=>{
    if(!$('consentBox').checked) return;
    $('startInterview').disabled=true; $('consentStatus').textContent='Recording consent…';
    try { await InterviewAPI.consent(state.session.id); const result=await InterviewAPI.start(state.session.id); state.session.state=result.state; state.currentTurn=result.turn; $('sessionSummary').textContent=`Session ${state.session.id} · ${state.rubric.criteria.length} criteria`; $('interviewState').textContent='Listening for your answer'; $('currentQuestion').textContent=result.turn.text; $('reasonTitle').textContent='Why this question?'; $('reasonText').textContent=result.turn.reason||'This question is linked to the visible job-related rubric.'; $('turnCounter').textContent=`Turn ${String((result.turn.idx||0)+1).padStart(2,'0')}`; show('interview'); await refreshTranscript(); InterviewSpeech.speak(result.turn.text); toast('Consent saved. Interview started.','success'); }
    catch(e){$('consentStatus').textContent=e.message; toast(e.message,'error'); $('startInterview').disabled=false;}
  });
  function renderTranscript(container, turns, clickable=true, prefix='transcript-turn-') {
    if (!turns.length) { container.innerHTML='<p class="muted">No transcript turns yet.</p>'; return; }
    container.innerHTML=turns.map(t=>`<article class="transcript-turn ${t.speaker==='candidate'?'candidate-turn':'agent-turn'}" id="${prefix}${esc(t.turn_id ?? t.idx ?? 0)}"><div class="transcript-turn-meta"><span>${t.speaker==='candidate'?'CANDIDATE':'INTERVIEWER'}</span><a href="#${prefix}${esc(t.turn_id ?? t.idx ?? 0)}">T${String(Number(t.turn_id ?? t.idx ?? 0)+1).padStart(3,'0')}</a></div><p>${esc(t.text)}</p>${t.kind==='followup'?'<span class="tag">Adaptive follow-up</span>':''}</article>`).join('');
  }
  async function refreshTranscript() {
    const data=await InterviewAPI.transcript(state.session.id); state.transcript=data.turns||[];
    renderTranscript($('transcriptList'),state.transcript);
    $('transcriptCount').textContent=`${state.transcript.length} turns`;
    $('transcriptList').scrollTop=$('transcriptList').scrollHeight;
    return state.transcript;
  }
  function setInterviewBusy(busy, message='Thinking…') {
    $('submitAnswer').disabled=busy; $('micBtn').disabled=busy || !InterviewSpeech.supported; $('finishInterview').disabled=busy;
    $('interviewState').textContent=busy?message:'Ready for your answer';
  }
  async function submitCurrentAnswer(textOverride) {
    const text=(textOverride ?? $('answerText').value).trim();
    if(!text){toast('Please type an answer or record one with the microphone.','error');return;}
    stopMic(); setInterviewBusy(true,'Analyzing answer…'); $('reasonTitle').textContent='Analyzing your answer'; $('reasonText').textContent='Checking for examples, ownership, outcomes, and trade-offs…';
    try {
      const result=await InterviewAPI.answer(state.session.id,text);
      $('answerText').value=''; state.currentTurn=result.turn; state.session.state=result.state;
      $('currentQuestion').textContent=result.utterance || result.turn?.text || 'Interview complete.';
      $('turnCounter').textContent=`Turn ${String((result.turn?.idx ?? state.transcript.length)+1).padStart(2,'0')}`;
      $('reasonTitle').textContent=result.kind==='follow_up'?'Why this follow-up?':result.kind==='closing'?'Interview completed':'Why this question?';
      $('reasonText').textContent=result.reason || 'This question is linked to the visible job-related rubric.';
      const cov=result.coverage||{covered:0,total:state.rubric.criteria.length,percent:0}; $('coverageText').textContent=`${cov.covered} / ${cov.total} criteria`; $('coverageBar').style.width=`${cov.percent}%`;
      await refreshTranscript();
      if(result.done || result.state==='COMPLETE') { $('interviewState').textContent='Complete'; $('currentQuestion').textContent=result.utterance||'Interview complete. Thank you.'; $('submitAnswer').disabled=true; $('answerText').disabled=true; $('micBtn').disabled=true; $('finishInterview').textContent='View assessment →'; toast('Interview completed. Preparing assessment…','success'); await loadReport(); }
      else { $('interviewState').textContent='Ready for your answer'; if(result.utterance) InterviewSpeech.speak(result.utterance); }
    } catch(e){toast(e.message,'error');$('interviewState').textContent='Connection error';}
    finally { if(state.session?.state!=='COMPLETE') setInterviewBusy(false); }
  }
  $('submitAnswer').addEventListener('click',()=>submitCurrentAnswer());
  $('answerText').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')submitCurrentAnswer();});
  $('repeatQuestion').addEventListener('click',()=>{if(state.currentTurn?.text) InterviewSpeech.speak(state.currentTurn.text);});
  $('micBtn').addEventListener('click',()=>{
    if(!InterviewSpeech.supported){$('speechStatus').textContent='Speech recognition is not supported here. Please type your answer.';return;}
    $('speechStatus').textContent='Listening… speak naturally, then stop or wait for recognition to finish.'; $('micBtn').disabled=true; $('stopMicBtn').disabled=false; $('interviewState').textContent='Listening…';
    try { state.recognition=InterviewSpeech.listen({onText:(text,isFinal)=>{ $('answerText').value=text; $('speechStatus').textContent=isFinal?'Speech captured. Review it, then submit.':'Transcribing live…'; },onError:e=>{ $('speechStatus').textContent=`Microphone issue: ${e.message}. You can type instead.`;toast(e.message,'error'); },onEnd:()=>{state.listening=false;$('micBtn').disabled=false;$('stopMicBtn').disabled=true;$('interviewState').textContent='Review your answer';}}); state.listening=Boolean(state.recognition); }
    catch(e){$('speechStatus').textContent='Could not start microphone. Please type your answer.';$('micBtn').disabled=false;$('stopMicBtn').disabled=true;}
  });
  function stopMic(){ if(state.recognition){try{state.recognition.stop();}catch{} state.recognition=null;} state.listening=false; if($('micBtn')) $('micBtn').disabled=!InterviewSpeech.supported; if($('stopMicBtn')) $('stopMicBtn').disabled=true; }
  $('stopMicBtn').addEventListener('click',()=>{stopMic();$('speechStatus').textContent='Stopped listening. Review the captured text before submitting.';});
  $('finishInterview').addEventListener('click',async()=>{
    if(state.session?.state==='COMPLETE'){await loadReport();return;}
    if(!confirm('Finish the interview now and generate the assessment?'))return;
    stopMic();setInterviewBusy(true,'Finishing interview…');
    try{const result=await InterviewAPI.finish(state.session.id);state.session.state='COMPLETE';state.assessment=result.assessment;await refreshTranscript();renderReport(result.assessment);show('report');}
    catch(e){toast(e.message,'error');}
    finally{if(state.session?.state==='COMPLETE'){ $('submitAnswer').disabled=true; $('answerText').disabled=true; $('micBtn').disabled=true; $('finishInterview').disabled=false; } else setInterviewBusy(false);}
  });
  async function loadReport(){try{const a=await InterviewAPI.assessment(state.session.id);state.assessment=a;renderReport(a);show('report');}catch(e){toast(e.message,'error');}}
  function renderReport(a){
    state.assessment=a; const scores=a.scores||[]; const max=scores.length*5; const scoredOnly=scores.filter(x=>x.score!==null&&x.score!==undefined); const earned=scoredOnly.reduce((sum,x)=>sum+Number(x.score),0); const avg=scoredOnly.length?(earned/scoredOnly.length).toFixed(1):'n/a';
    $('reportSummary').innerHTML=`<div class="report-stat"><span>RUBRIC SUMMARY</span><strong>${esc(a.overall??avg)}${(a.overall??avg)==='n/a'?'':' / 5'}</strong></div><div class="report-stat"><span>CRITERIA SCORED</span><strong>${scoredOnly.length} / ${scores.length}</strong></div><div class="report-stat"><span>VERIFIED QUOTES</span><strong>${scores.reduce((n,x)=>n+(x.evidence_quotes||[]).length,0)}</strong></div><div class="report-stat report-summary-text"><span>SUMMARY</span><p>${esc(a.summary||'No summary supplied.')}</p></div>`;
    $('scoreTable').innerHTML=scores.map(sc=>{const c=state.rubric.criteria.find(x=>x.id===sc.criterion_id)||{name:sc.criterion_id};const quotes=(sc.evidence_quotes||[]);return `<article class="score-card"><div class="score-top"><div><h4>${esc(c.name)}</h4><p>${esc(sc.rationale||'No rationale provided.')}</p></div><strong class="score-number">${sc.score==null?'n/a':esc(sc.score)}<small>${sc.score==null?'':'/5'}</small></strong></div><div class="score-meter"><span style="width:${sc.score==null?0:Math.max(0,Math.min(100,Number(sc.score)*20))}%"></span></div><div class="evidence-list"><b>Verified evidence</b>${quotes.length?quotes.map(q=>{const turn=state.transcript.find(t=>t.speaker==='candidate'&&normalise(t.text).includes(normalise(q)));return `<a class="evidence-quote" href="#report-transcript-turn-${esc(turn?.turn_id??turn?.idx??0)}">“${esc(q)}” <span>↗ transcript</span></a>`}).join(''):'<p class="muted">Insufficient verified evidence for this criterion.</p>'}</div></article>`;}).join('');
    const li=(arr,cls)=>arr.map(x=>`<div class="insight-item ${cls||''}"><strong>${esc(x)}</strong></div>`).join('');
    const strengths=a.strengths||[], gaps=a.gaps||[], review=a.needs_human_review||[], asks=a.suggested_human_questions||[];
    $('reportStrengths').innerHTML=strengths.length?li(strengths):'<p class="muted">No criteria currently meet the strong-evidence threshold (4/5). Review the transcript before interpreting this as a weakness.</p>';
    $('reportGaps').innerHTML=(gaps.length?li(gaps,'gap-item'):'<p class="muted">No criteria are flagged as low-scoring or lacking verified evidence. Human review is still required.</p>')
      +(review.length?'<h4>Needs human review</h4>'+review.map(r=>`<div class="insight-item gap-item"><strong>${esc(r.topic)}</strong><span>${esc(r.why)}</span></div>`).join(''):'')
      +(asks.length?'<h4>Suggested questions for the human round</h4>'+asks.map(q=>`<div class="insight-item"><span>${esc(q)}</span></div>`).join(''):'')
      +`<p class="muted">${esc(a.disclaimer||'Assessment to support a human reviewer. Not a hiring decision.')}</p>`;
    renderTranscript($('reportTranscript'),state.transcript,true,'report-transcript-turn-'); const flags=a.flags||[]; $('reportFlags').innerHTML=flags.length?flags.map(f=>`<div class="flag-item">⚑ ${esc(f)}</div>`).join(''):'<div class="flag-item flag-ok">No additional automated flags. Human review is still required.</div>';
    $('verifiedBadge').textContent=`${scores.reduce((n,x)=>n+(x.evidence_quotes||[]).length,0)} evidence quotes`; 
  }
  function normalise(s){return String(s||'').toLowerCase().replace(/[^\w\s]/g,'').replace(/\s+/g,' ').trim();}
  $('exportJson').addEventListener('click',()=>{if(!state.assessment)return;const data={session_id:state.session.id,assessment:state.assessment,transcript:state.transcript,rubric:state.rubric,reviewer_decision:state.reviewerDecision};const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`interviewlens-${state.session.id}-assessment.json`;a.click();URL.revokeObjectURL(url);});
  $('saveDecision').addEventListener('click',()=>{
    const decision=$('reviewDecision').value, rationale=$('reviewRationale').value.trim(), reviewer=$('reviewerName').value.trim();
    if(!decision){toast('Select a reviewer decision first.','error');$('reviewDecision').focus();return;}
    if(!rationale){toast('Add a job-related reason for the decision.','error');$('reviewRationale').focus();return;}
    state.reviewerDecision={decision,reviewer:reviewer||null,rationale,recorded_at:new Date().toISOString(),session_id:state.session?.id||null,decision_maker:'human_reviewer'};
    $('decisionStatus').textContent='Decision recorded'; $('decisionStatus').className='pill pill-green';
    $('decisionSavedText').textContent=`Saved in this open report at ${new Date(state.reviewerDecision.recorded_at).toLocaleString()}. Export JSON to keep a copy.`;
    toast('Human reviewer decision recorded. Export JSON to preserve it.','success');
  });
  $('printReport').addEventListener('click',()=>window.print());
  $('backToInterview').addEventListener('click',()=>show('interview'));

  function reset(){ stopMic(); InterviewSpeech.stop(); state.session=null; state.rubric=null; state.plan=null; state.currentTurn=null; state.transcript=[]; state.assessment=null; state.reviewerDecision=null; $('reviewDecision').value=''; $('reviewerName').value=''; $('reviewRationale').value=''; $('decisionStatus').textContent='Decision pending'; $('decisionStatus').className='pill pill-amber'; $('decisionSavedText').textContent='No reviewer decision recorded yet.'; $('jd').value=''; $('resume').value=''; $('setupStatus').textContent='Ready when you are.'; $('consentBox').checked=false; $('startInterview').disabled=true; $('sessionSummary').textContent=''; $('answerText').value=''; show('setup'); }
  $('resetBtn').addEventListener('click',reset); $('newSessionReport').addEventListener('click',reset); $('brandHome').addEventListener('click',e=>{e.preventDefault();reset();});
  checkHealth();
})();

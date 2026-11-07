let s='';
process.stdin.on('data',d=>s+=d).on('end',()=>{
  const j = JSON.parse(s).data;
  const want = ['vehicle','traffic_light','helmet','lane'];
  const seqOk = Array.isArray(j.model_sequence) && j.model_sequence.length===4 && j.model_sequence.every((v,i)=>v===want[i]);
  const szOk = j.yolo_imgsz === 960;
  const frOk = j.frame_rate === 6;
  console.log('  model_sequence 匹配 =', seqOk, JSON.stringify(j.model_sequence));
  console.log('  yolo_imgsz === 960  =', szOk, '实际:', j.yolo_imgsz, '(类型', typeof j.yolo_imgsz + ')');
  console.log('  frame_rate === 6    =', frOk, '实际:', j.frame_rate, '(类型', typeof j.frame_rate + ')');
  console.log('  ==> 全部一致 =', seqOk && szOk && frOk);
});
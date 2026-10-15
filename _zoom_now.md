L70:         <div class="video-wrap">
L71:           <img :src="streamUrl" class="video-img" alt="实时检测画面"
L73:           <div v-if="!streamOk" class="video-mask">
L81:             <div v-if="zoomSrc && focusPip" class="zoom-pip">
L82:               <img :src="zoomSrc" class="zoom-pip-img" alt="聚焦目标" />
L83:               <span class="zoom-pip-cap">聚焦 · 违规目标</span>
L306: const zoomSrc = ref('')
L382:       if (vehicles.violators.length && !zoomSrc.value) triggerZoom(vehicles.violators[0])
L388: function triggerZoom(target) {
L391:   zoomSrc.value = url
L393:   zoomTimer = setTimeout(() => { zoomSrc.value = '' }, 1400)   // 定格后可拉远
L766: .video-wrap { position: relative; background: #0B0D10; min-height: 300px; }
L767: .video-img { display: block; width: 100%; height: auto; }
L768: .video-mask {
L773: .video-mask .hint { font-size: 12px; color: #5A6070; }
L784: .zoom-pip {
L792: .zoom-pip-img { display: block; width: 100%; height: auto; }
L793: .zoom-pip-cap {

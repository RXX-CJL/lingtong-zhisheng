L314: const aiBusy = ref(false)
L315: const points = ref([])
L316: const frameW = ref(1280)
L317: const frameH = ref(576)
L318: const sceneImg = ref(null)
L319: const firstFrameUrl = computed(() =>
L321: const polygonPoints = computed(() => points.value.map(p => `${p[0]},${p[1]}`).join(' '))
L497: function openSceneDialog() {
L502: function onCanvasClick(ev) {
L515: function undoPoint() { points.value.pop() }
L516: function clearPoints() { points.value = [] }
L518: async function aiDetect() {
L536: async function saveScene() {

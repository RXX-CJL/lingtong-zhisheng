import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const BACKEND_URL = 'http://127.0.0.1:8001';
const SOCKET_URL = 'http://localhost:5000';

// M14: 违规类型颜色（与 app.py DEMO_VIOLATION_TYPES / M05 颜色表对齐）
const VIOLATION_COLOR_MAP = {
    red_light: 0xF44336,         // 深红
    wrong_way: 0xFF9800,         // 橙色
    illegal_parking: 0x9C27B0,   // 紫色
    no_helmet: 0x00BCD4,         // 青色
    speeding: 0xE91E63,          // 粉红
    lane_departure: 0xFFC107,    // 黄色
    street_stall: 0x2196F3,      // 蓝色
    crowd_gathering: 0xFFEB3B,   // 黄色
};

const VIOLATION_NAME_CN = {
    red_light: '闯红灯',
    wrong_way: '逆行',
    illegal_parking: '违规停车',
    no_helmet: '未戴头盔',
    speeding: '超速',
    lane_departure: '压线行驶',
    street_stall: '占道经营',
    crowd_gathering: '人员聚集',
};

class TrafficScene {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.labelRenderer = null;  // M14: CSS2DRenderer 用于车牌标签
        this.controls = null;
        this.vehicles = [];
        this.trafficLights = [];
        this.frameCount = 0;
        this.cameras = [];
        this.videoPanels = {};
        this.activeVideoCamera = null;
        this.isVideoMinimized = false;
        
        this.trafficPhase = 0;
        this.phaseStartTime = 0;
        this.trafficCycleStart = Date.now();  // M14: 真实时间基准
        this.phaseDurations = {
            green: 300,
            yellow: 30,
            red: 300
        };
        
        this.vehicleColors = {
            normal: 0x4CAF50,
            violation: 0xFF5722,
            red_light: 0xF44336,
            no_helmet: 0xFF9800,
            illegal_parking: 0x9C27B0,
            speeding: 0xE91E63
        };
        
        this.stopLines = [
            { x: 0, z: 23, direction: 'north' },
            { x: 0, z: -23, direction: 'south' },
            { x: 23, z: 0, direction: 'west' },
            { x: -23, z: 0, direction: 'east' }
        ];
        
        this.socket = null;
        this.socketConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.lastDataUpdate = 0;
        this.dataUpdateInterval = 200;
        
        // M14: 违规标注层 - key=track_id, value={arrowGroup, labelDiv, expireAt}
        this.violationAnnotations = new Map();
        // M14: 仪表盘今日计数
        this.todayCounts = {
            red_light: 0, wrong_way: 0, no_helmet: 0,
            illegal_parking: 0, speeding: 0, lane_departure: 0,
            street_stall: 0, crowd_gathering: 0,
        };
        
        this.init();
        this.createScene();
        this.setupMultiCameraStatus();
        this.createVideoPanel();
        this.createLabelRenderer();   // M14
        this.startAnimation();
        this.startDataSimulation();
        this.startVideoStreamListener();
        this.startVehicleSpawner();
        this.setupWebSocket();
        this.startDashboardSync();     // M14
        this.startAnnotationExpiry();  // M14
    }
    
    init() {
        const canvas = document.getElementById('canvas');
        const container = document.getElementById('scene-container');
        
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);
        this.scene.fog = new THREE.Fog(0x1a1a2e, 100, 300);
        
        const aspect = container.clientWidth / container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 500);
        this.camera.position.set(50, 40, 50);
        this.camera.lookAt(0, 0, 0);
        
        this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.minDistance = 20;
        this.controls.maxDistance = 120;
        this.controls.maxPolarAngle = Math.PI / 2.2;
        
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(30, 50, 30);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 200;
        directionalLight.shadow.camera.left = -50;
        directionalLight.shadow.camera.right = 50;
        directionalLight.shadow.camera.top = 50;
        directionalLight.shadow.camera.bottom = -50;
        this.scene.add(directionalLight);
        
        const pointLight1 = new THREE.PointLight(0x2196F3, 0.5, 100);
        pointLight1.position.set(-30, 20, -30);
        this.scene.add(pointLight1);
        
        const pointLight2 = new THREE.PointLight(0xE91E63, 0.5, 100);
        pointLight2.position.set(30, 20, 30);
        this.scene.add(pointLight2);
        
        window.addEventListener('resize', () => this.onWindowResize());
        
        document.getElementById('btn-reset').addEventListener('click', () => this.resetCamera());
    }
    
    createScene() {
        this.createGround();
        this.createRoads();
        this.createSidewalks();
        this.createBuildings();
        this.createTrafficLights();
        this.createTrees();
        this.createStreetLights();
        this.createCameraMarkers();
        this.createStopLines();
    }
    
    createGround() {
        const geometry = new THREE.PlaneGeometry(120, 120);
        const material = new THREE.MeshStandardMaterial({
            color: 0x2E7D32,
            roughness: 0.8,
            metalness: 0.1
        });
        const ground = new THREE.Mesh(geometry, material);
        ground.rotation.x = -Math.PI / 2;
        ground.receiveShadow = true;
        this.scene.add(ground);
    }
    
    createRoads() {
        const roadMaterial = new THREE.MeshStandardMaterial({
            color: 0x333333,
            roughness: 0.9,
            metalness: 0.1
        });
        
        const createRoad = (width, length, x, z, rotation) => {
            const geometry = new THREE.BoxGeometry(width, 0.1, length);
            const road = new THREE.Mesh(geometry, roadMaterial);
            road.position.set(x, 0.05, z);
            road.rotation.y = rotation;
            road.receiveShadow = true;
            this.scene.add(road);
            return road;
        };
        
        createRoad(12, 100, 0, 0, 0);
        createRoad(12, 100, 0, 0, Math.PI / 2);
        
        const lineMaterial = new THREE.MeshBasicMaterial({ color: 0xFFFFFF });
        
        const createLine = (x1, z1, x2, z2) => {
            const geometry = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(x1, 0.11, z1),
                new THREE.Vector3(x2, 0.11, z2)
            ]);
            const line = new THREE.Line(geometry, lineMaterial);
            this.scene.add(line);
        };
        
        for (let i = -45; i <= 45; i += 5) {
            createLine(-6, i, 6, i);
            createLine(i, -6, i, 6);
        }
        
        createLine(-6, 0, 6, 0);
        createLine(0, -6, 0, 6);
        
        const dashedLineMaterial = new THREE.LineDashedMaterial({
            color: 0xFFFFFF,
            dashSize: 2,
            gapSize: 3
        });
        
        const createDashedLine = (x1, z1, x2, z2) => {
            const geometry = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(x1, 0.11, z1),
                new THREE.Vector3(x2, 0.11, z2)
            ]);
            const line = new THREE.Line(geometry, dashedLineMaterial);
            line.computeLineDistances();
            this.scene.add(line);
        };
        
        createDashedLine(-3, -45, -3, -25);
        createDashedLine(-3, 25, -3, 45);
        createDashedLine(3, -45, 3, -25);
        createDashedLine(3, 25, 3, 45);
        createDashedLine(-45, -3, -25, -3);
        createDashedLine(25, -3, 45, -3);
        createDashedLine(-45, 3, -25, 3);
        createDashedLine(25, 3, 45, 3);
        
        const crosswalkMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFFFFF,
            roughness: 0.8
        });
        
        const createCrosswalk = (x, z, width, height, rotation) => {
            const geometry = new THREE.BoxGeometry(width, 0.02, height);
            const crosswalk = new THREE.Mesh(geometry, crosswalkMaterial);
            crosswalk.position.set(x, 0.12, z);
            crosswalk.rotation.y = rotation;
            crosswalk.receiveShadow = true;
            this.scene.add(crosswalk);
        };
        
        createCrosswalk(0, -25, 4, 12, 0);
        createCrosswalk(0, 25, 4, 12, 0);
        createCrosswalk(-25, 0, 4, 12, Math.PI / 2);
        createCrosswalk(25, 0, 4, 12, Math.PI / 2);
    }
    
    createStopLines() {
        const stopLineMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFEB3B,
            roughness: 0.8
        });
        
        const createStopLine = (x, z, width, height, rotation) => {
            const geometry = new THREE.BoxGeometry(width, 0.02, height);
            const line = new THREE.Mesh(geometry, stopLineMaterial);
            line.position.set(x, 0.12, z);
            line.rotation.y = rotation;
            line.receiveShadow = true;
            this.scene.add(line);
        };
        
        createStopLine(0, 23, 10, 0.5, Math.PI / 2);
        createStopLine(0, -23, 10, 0.5, Math.PI / 2);
        createStopLine(23, 0, 10, 0.5, 0);
        createStopLine(-23, 0, 10, 0.5, 0);
    }
    
    createBuildings() {
        const buildingMaterial = new THREE.MeshStandardMaterial({
            color: 0x546E7A,
            roughness: 0.7,
            metalness: 0.2
        });
        
        const windowMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFD54F,
            emissive: 0xFFD54F,
            emissiveIntensity: 0.3
        });
        
        const createBuilding = (width, height, depth, x, z) => {
            const geometry = new THREE.BoxGeometry(width, height, depth);
            const building = new THREE.Mesh(geometry, buildingMaterial);
            building.position.set(x, height / 2, z);
            building.castShadow = true;
            building.receiveShadow = true;
            this.scene.add(building);
            
            for (let i = 0; i < 3; i++) {
                for (let j = 0; j < 3; j++) {
                    const windowGeo = new THREE.BoxGeometry(width * 0.15, height * 0.15, 0.1);
                    const windowMesh = new THREE.Mesh(windowGeo, windowMaterial);
                    windowMesh.position.set(
                        x + (i - 1) * (width * 0.25),
                        height * 0.15 + i * (height * 0.25),
                        z + depth / 2 + 0.05
                    );
                    this.scene.add(windowMesh);
                }
            }
        };
        
        createBuilding(15, 12, 15, -40, -40);
        createBuilding(20, 15, 12, 40, -35);
        createBuilding(12, 18, 15, -35, 40);
        createBuilding(18, 10, 18, 35, 35);
    }
    
    createTrafficLights() {
        const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x78909C });
        const lightMaterialGreen = new THREE.MeshStandardMaterial({
            color: 0x4CAF50,
            emissive: 0x4CAF50,
            emissiveIntensity: 1
        });
        const lightMaterialRed = new THREE.MeshStandardMaterial({
            color: 0xF44336,
            emissive: 0xF44336,
            emissiveIntensity: 1
        });
        const lightMaterialYellow = new THREE.MeshStandardMaterial({
            color: 0xFFEB3B,
            emissive: 0xFFEB3B,
            emissiveIntensity: 1
        });
        const lightMaterialOff = new THREE.MeshStandardMaterial({
            color: 0x333333,
            emissive: 0x111111,
            emissiveIntensity: 0.1
        });
        
        const createCountdownDisplay = (x, z) => {
            const canvas = document.createElement('canvas');
            canvas.width = 64;
            canvas.height = 64;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, 64, 64);
            
            const texture = new THREE.CanvasTexture(canvas);
            const material = new THREE.MeshStandardMaterial({ 
                map: texture,
                transparent: true
            });
            const geometry = new THREE.PlaneGeometry(1.5, 1.5);
            const mesh = new THREE.Mesh(geometry, material);
            mesh.position.set(x, 5.5, z + 0.3);
            mesh.rotation.y = Math.PI;
            this.scene.add(mesh);
            
            return { mesh, canvas, ctx, texture };
        };
        
        const createTrafficLight = (x, z, rotation, direction) => {
            const poleGeo = new THREE.CylinderGeometry(0.2, 0.3, 8, 8);
            const pole = new THREE.Mesh(poleGeo, poleMaterial);
            pole.position.set(x, 4, z);
            pole.castShadow = true;
            this.scene.add(pole);
            
            const boxGeo = new THREE.BoxGeometry(0.8, 2.5, 0.4);
            const box = new THREE.Mesh(boxGeo, new THREE.MeshStandardMaterial({ color: 0x263238 }));
            box.position.set(x, 7, z);
            box.castShadow = true;
            this.scene.add(box);
            
            const lights = [];
            const colors = [lightMaterialRed, lightMaterialYellow, lightMaterialGreen];
            const positions = [0.8, 0, -0.8];
            
            for (let i = 0; i < 3; i++) {
                const lightGeo = new THREE.SphereGeometry(0.3, 16, 16);
                const light = new THREE.Mesh(lightGeo, lightMaterialOff);
                light.position.set(x, 7 + positions[i], z + 0.21);
                light.castShadow = true;
                this.scene.add(light);
                lights.push({ mesh: light, onMaterial: colors[i], offMaterial: lightMaterialOff });
            }
            
            const countdown = createCountdownDisplay(x, z);
            
            return { 
                lights, 
                countdown,
                direction,
                currentState: 'red',
                countdownValue: 30
            };
        };
        
        this.trafficLights.push(createTrafficLight(7, 27, 0, 'north'));
        this.trafficLights.push(createTrafficLight(-7, -27, 0, 'south'));
        this.trafficLights.push(createTrafficLight(-27, -7, Math.PI / 2, 'east'));
        this.trafficLights.push(createTrafficLight(27, 7, Math.PI / 2, 'west'));
    }
    
    updateCountdownDisplay(countdown, value) {
        const { canvas, ctx, texture } = countdown;
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, 64, 64);
        ctx.fillStyle = '#FFF';
        ctx.font = 'bold 36px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(value.toString(), 32, 32);
        texture.needsUpdate = true;
    }
    
    createSidewalks() {
        const sidewalkMaterial = new THREE.MeshStandardMaterial({
            color: 0x9E9E9E,
            roughness: 0.8,
            metalness: 0.1
        });
        
        const createSidewalk = (width, length, x, z, rotation) => {
            const geometry = new THREE.BoxGeometry(width, 0.05, length);
            const sidewalk = new THREE.Mesh(geometry, sidewalkMaterial);
            sidewalk.position.set(x, 0.025, z);
            sidewalk.rotation.y = rotation;
            sidewalk.receiveShadow = true;
            this.scene.add(sidewalk);
        };
        
        createSidewalk(2, 100, 7.5, 0, 0);
        createSidewalk(2, 100, -7.5, 0, 0);
        createSidewalk(2, 100, 0, 7.5, Math.PI / 2);
        createSidewalk(2, 100, 0, -7.5, Math.PI / 2);
    }
    
    createTrees() {
        const trunkMaterial = new THREE.MeshStandardMaterial({
            color: 0x8B4513,
            roughness: 0.8,
            metalness: 0.1
        });
        
        const leavesMaterial = new THREE.MeshStandardMaterial({
            color: 0x228B22,
            roughness: 0.7,
            metalness: 0.1
        });
        
        const createTree = (x, z, scale = 1) => {
            const trunkGeo = new THREE.CylinderGeometry(0.2 * scale, 0.3 * scale, 2 * scale, 8);
            const trunk = new THREE.Mesh(trunkGeo, trunkMaterial);
            trunk.position.set(x, scale, z);
            trunk.castShadow = true;
            this.scene.add(trunk);
            
            const leavesGeo = new THREE.SphereGeometry(1.2 * scale, 16, 16);
            const leaves = new THREE.Mesh(leavesGeo, leavesMaterial);
            leaves.position.set(x, 2.5 * scale, z);
            leaves.castShadow = true;
            this.scene.add(leaves);
            
            const leavesGeo2 = new THREE.SphereGeometry(1 * scale, 16, 16);
            const leaves2 = new THREE.Mesh(leavesGeo2, leavesMaterial);
            leaves2.position.set(x, 3.5 * scale, z);
            leaves2.castShadow = true;
            this.scene.add(leaves2);
        };
        
        const treePositions = [
            [-45, -45], [-45, -35], [-45, 35], [-45, 45],
            [45, -45], [45, -35], [45, 35], [45, 45],
            [-35, -45], [-35, 45], [35, -45], [35, 45],
            [-25, -40], [-25, 40], [25, -40], [25, 40],
            [-40, -25], [40, -25], [-40, 25], [40, 25]
        ];
        
        treePositions.forEach(([x, z]) => createTree(x, z, 0.8 + Math.random() * 0.4));
    }
    
    createStreetLights() {
        const poleMaterial = new THREE.MeshStandardMaterial({ color: 0x607D8B });
        const lightMaterial = new THREE.MeshStandardMaterial({
            color: 0xFFFFFF,
            emissive: 0xFFFFFF,
            emissiveIntensity: 0.8
        });
        
        const createStreetLight = (x, z) => {
            const poleGeo = new THREE.CylinderGeometry(0.1, 0.15, 6, 8);
            const pole = new THREE.Mesh(poleGeo, poleMaterial);
            pole.position.set(x, 3, z);
            pole.castShadow = true;
            this.scene.add(pole);
            
            const armGeo = new THREE.BoxGeometry(3, 0.05, 0.05);
            const arm = new THREE.Mesh(armGeo, poleMaterial);
            arm.position.set(x, 5.5, z);
            arm.castShadow = true;
            this.scene.add(arm);
            
            const lightGeo = new THREE.SphereGeometry(0.25, 16, 16);
            const light = new THREE.Mesh(lightGeo, lightMaterial);
            light.position.set(x + 1.5, 5.5, z);
            light.castShadow = true;
            this.scene.add(light);
            
            const pointLight = new THREE.PointLight(0xFFFFFF, 0.4, 20);
            pointLight.position.set(x + 1.5, 5.5, z);
            this.scene.add(pointLight);
        };
        
        const lightPositions = [
            [-30, 10], [-30, -10], [30, 10], [30, -10],
            [10, -30], [-10, -30], [10, 30], [-10, 30],
            [-40, 0], [40, 0], [0, -40], [0, 40]
        ];
        
        lightPositions.forEach(([x, z]) => createStreetLight(x, z));
    }
    
    createCameraMarkers() {
        const cameraMaterial = new THREE.MeshStandardMaterial({
            color: 0xFF5722,
            emissive: 0xFF5722,
            emissiveIntensity: 0.5
        });
        
        const createCameraMarker = (x, z, name, cameraId) => {
            const baseGeo = new THREE.CylinderGeometry(0.3, 0.4, 0.2, 8);
            const base = new THREE.Mesh(baseGeo, new THREE.MeshStandardMaterial({ color: 0x424242 }));
            base.position.set(x, 0.1, z);
            base.receiveShadow = true;
            this.scene.add(base);
            
            const poleGeo = new THREE.CylinderGeometry(0.15, 0.2, 4, 8);
            const pole = new THREE.Mesh(poleGeo, new THREE.MeshStandardMaterial({ color: 0x757575 }));
            pole.position.set(x, 2, z);
            pole.castShadow = true;
            this.scene.add(pole);
            
            const cameraGeo = new THREE.BoxGeometry(0.6, 0.4, 0.3);
            const camera = new THREE.Mesh(cameraGeo, cameraMaterial);
            camera.position.set(x, 3.8, z + 0.2);
            camera.castShadow = true;
            this.scene.add(camera);
            
            this.cameras.push({
                id: cameraId,
                name: name,
                position: new THREE.Vector3(x, 5, z - 2),
                lookAt: new THREE.Vector3(0, 0, 0)
            });
        };
        
        createCameraMarker(-25, -25, '东北角', 'cam1');
        createCameraMarker(25, -25, '东南角', 'cam2');
        createCameraMarker(25, 25, '西南角', 'cam3');
        createCameraMarker(-25, 25, '西北角', 'cam4');
    }
    
    getCameraPresets() {
        return this.cameras.map(cam => ({
            id: cam.id,
            name: cam.name,
            position: cam.position,
            lookAt: cam.lookAt
        }));
    }
    
    setCameraView(cameraId) {
        const cam = this.cameras.find(c => c.id === cameraId);
        if (cam) {
            this.camera.position.copy(cam.position);
            this.camera.lookAt(cam.lookAt);
            this.controls.target.copy(cam.lookAt);
            this.controls.update();
        }
    }
    
    createVehicle(id, type, position, direction, color = 0x4CAF50) {
        let geometry;
        if (type === 'car') {
            geometry = new THREE.BoxGeometry(1.8, 1.2, 3.5);
        } else if (type === 'motorcycle') {
            geometry = new THREE.BoxGeometry(0.8, 1.0, 2.0);
        } else {
            geometry = new THREE.BoxGeometry(1.5, 1.1, 4.0);
        }
        
        const material = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.6,
            metalness: 0.3
        });
        
        const vehicle = new THREE.Mesh(geometry, material);
        vehicle.position.set(position.x, position.y, position.z);
        vehicle.castShadow = true;
        vehicle.receiveShadow = true;
        
        this.scene.add(vehicle);
        
        return {
            mesh: vehicle,
            id: id,
            type: type,
            speed: 0,
            targetSpeed: 50 + Math.random() * 30,
            direction: direction.clone().normalize(),
            violation: null,
            stoppedAtLight: false,
            waitTime: 0,
            isCrossing: false,
            path: 'straight'
        };
    }
    
    removeVehicle(id) {
        const index = this.vehicles.findIndex(v => v.id === id);
        if (index !== -1) {
            this.scene.remove(this.vehicles[index].mesh);
            this.vehicles.splice(index, 1);
        }
    }
    
    updateVehicle(id, data) {
        const vehicle = this.vehicles.find(v => v.id === id);
        if (vehicle) {
            if (data.position) {
                vehicle.mesh.position.set(data.position.x, data.position.y, data.position.z);
            }
            if (data.rotation) {
                vehicle.mesh.rotation.y = data.rotation.y;
            }
            if (data.speed) {
                vehicle.speed = data.speed;
            }
            if (data.violation !== undefined) {
                vehicle.violation = data.violation;
                const color = this.vehicleColors[data.violation] || this.vehicleColors.normal;
                vehicle.mesh.material.color.setHex(color);
            }
        }
    }
    
    getVehicleDirection(vehicle) {
        const dir = vehicle.direction;
        if (Math.abs(dir.z) > Math.abs(dir.x)) {
            return dir.z > 0 ? 'north' : 'south';
        } else {
            return dir.x > 0 ? 'east' : 'west';
        }
    }
    
    getTrafficLightState(direction) {
        const phase = Math.floor(this.frameCount / 360) % 4;
        const states = [
            { north: 'green', south: 'green', east: 'red', west: 'red' },
            { north: 'yellow', south: 'yellow', east: 'red', west: 'red' },
            { north: 'red', south: 'red', east: 'green', west: 'green' },
            { north: 'red', south: 'red', east: 'yellow', west: 'yellow' }
        ];
        return states[phase][direction] || 'red';
    }
    
    checkStopAtLight(vehicle) {
        const pos = vehicle.mesh.position;
        const direction = this.getVehicleDirection(vehicle);
        
        let stopLinePos = 0;
        let approaching = false;
        
        switch (direction) {
            case 'north':
                stopLinePos = 23;
                approaching = pos.z < stopLinePos && pos.z > 18;
                break;
            case 'south':
                stopLinePos = -23;
                approaching = pos.z > stopLinePos && pos.z < -18;
                break;
            case 'east':
                stopLinePos = 23;
                approaching = pos.x < stopLinePos && pos.x > 18;
                break;
            case 'west':
                stopLinePos = -23;
                approaching = pos.x > stopLinePos && pos.x < -18;
                break;
        }
        
        if (approaching) {
            const lightState = this.getTrafficLightState(direction);
            if (lightState === 'red') {
                return true;
            } else if (lightState === 'yellow') {
                return vehicle.speed > 20;
            }
        }
        return false;
    }
    
    checkCollision(vehicle) {
        const pos = vehicle.mesh.position;
        const safetyDistance = 4;
        
        for (const other of this.vehicles) {
            if (other.id === vehicle.id) continue;
            
            const otherPos = other.mesh.position;
            const distance = pos.distanceTo(otherPos);
            
            if (distance < safetyDistance) {
                const dir = vehicle.direction.clone();
                const otherDir = other.direction.clone();
                
                if (dir.dot(otherDir) > 0.5) {
                    return true;
                }
            }
        }
        return false;
    }
    
    updateTrafficLights() {
        // M14: 用真实时间（毫秒）替代帧数，保证倒计时准确
        // 阶段顺序：南北绿 → 南北黄 → 东西绿 → 东西黄 → 循环
        // (红→绿→黄→红... 的物理顺序在各方向上分别满足)
        const PHASE_GREEN_MS = 30000;   // 绿灯 30 秒
        const PHASE_YELLOW_MS = 3000;   // 黄灯 3 秒
        const CYCLE_MS = (PHASE_GREEN_MS + PHASE_YELLOW_MS) * 2;  // 66 秒
        const now = Date.now();
        const cycleTime = (now - this.trafficCycleStart) % CYCLE_MS;
        
        let phase = 0;
        let phaseTime = 0;
        let phaseRemaining = 0;
        if (cycleTime < PHASE_GREEN_MS) {
            phase = 0; phaseTime = cycleTime; phaseRemaining = PHASE_GREEN_MS - cycleTime;
        } else if (cycleTime < PHASE_GREEN_MS + PHASE_YELLOW_MS) {
            phase = 1; phaseTime = cycleTime - PHASE_GREEN_MS; phaseRemaining = PHASE_YELLOW_MS - phaseTime;
        } else if (cycleTime < PHASE_GREEN_MS * 2 + PHASE_YELLOW_MS) {
            phase = 2; phaseTime = cycleTime - PHASE_GREEN_MS - PHASE_YELLOW_MS; phaseRemaining = PHASE_GREEN_MS - phaseTime;
        } else {
            phase = 3; phaseTime = cycleTime - PHASE_GREEN_MS * 2 - PHASE_YELLOW_MS; phaseRemaining = PHASE_YELLOW_MS - phaseTime;
        }
        
        const getLightState = (direction) => {
            const states = [
                { north: 'green', south: 'green', east: 'red', west: 'red' },
                { north: 'yellow', south: 'yellow', east: 'red', west: 'red' },
                { north: 'red', south: 'red', east: 'green', west: 'green' },
                { north: 'red', south: 'red', east: 'yellow', west: 'yellow' }
            ];
            return states[phase][direction] || 'red';
        };
        
        // 倒计时秒数（向上取整，最小 1）
        const countdownValue = Math.max(1, Math.ceil(phaseRemaining / 1000));
        
        this.trafficLights.forEach(tl => {
            const state = getLightState(tl.direction);
            tl.currentState = state;
            
            tl.lights.forEach((light, i) => {
                const shouldBeOn = (state === 'red' && i === 0) ||
                                   (state === 'yellow' && i === 1) ||
                                   (state === 'green' && i === 2);
                light.mesh.material = shouldBeOn ? light.onMaterial : light.offMaterial;
            });
            
            this.updateCountdownDisplay(tl.countdown, countdownValue);
        });
        
        document.getElementById('traffic-phase').textContent = 
            ['南北直行', '南北黄灯', '东西直行', '东西黄灯'][phase];
    }
    
    onWindowResize() {
        const container = document.getElementById('scene-container');
        this.camera.aspect = container.clientWidth / container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(container.clientWidth, container.clientHeight);
    }
    
    resetCamera() {
        this.camera.position.set(50, 40, 50);
        this.camera.lookAt(0, 0, 0);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }
    
    spawnVehicle() {
        if (this.vehicles.length >= 10) return;
        
        const spawnPoints = [
            { x: 0, z: -45, direction: new THREE.Vector3(0, 0, 1), type: 'car' },
            { x: 0, z: 45, direction: new THREE.Vector3(0, 0, -1), type: 'car' },
            { x: -45, z: 0, direction: new THREE.Vector3(1, 0, 0), type: 'car' },
            { x: 45, z: 0, direction: new THREE.Vector3(-1, 0, 0), type: 'car' }
        ];
        
        const spawn = spawnPoints[Math.floor(Math.random() * spawnPoints.length)];
        
        const colors = [0x4CAF50, 0x2196F3, 0xFF5722, 0xFF9800, 0x9C27B0, 0x00BCD4];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        const vehicle = this.createVehicle(
            `vehicle_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            spawn.type,
            { x: spawn.x, y: 0.6, z: spawn.z },
            spawn.direction,
            color
        );
        
        this.vehicles.push(vehicle);
    }
    
    startVehicleSpawner() {
        setInterval(() => {
            if (!this.socketConnected && this.vehicles.length < 10) {
                this.spawnVehicle();
            }
        }, 3000);
    }
    
    setupWebSocket() {
        const connect = () => {
            const socketProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${socketProtocol}//${window.location.host}/socket.io/?EIO=4&transport=websocket`;
            
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log('[WebSocket] 连接成功');
                this.socketConnected = true;
                this.reconnectAttempts = 0;
                this.updateConnectionStatus(true);
            };
            
            this.socket.onmessage = (event) => {
                try {
                    let data = event.data;
                    if (typeof data === 'string') {
                        if (data.startsWith('0')) {
                            data = data.substring(1);
                        }
                        if (data.startsWith('42')) {
                            data = data.substring(2);
                        }
                        const parsed = JSON.parse(data);
                        if (parsed[0] === 'traffic_update') {
                            this.handleTrafficUpdate(parsed[1]);
                        } else if (parsed[0] === 'violation_detected') {
                            this.triggerViolationEvent(parsed[1]);
                        } else if (parsed[0] === 'real_violation_event') {
                            // M14: 后端推送的真实违规事件
                            this.handleRealViolationEvent(parsed[1]);
                        } else if (parsed[0] === 'realtime_status_sync') {
                            // M14: 实时检测状态同步
                            this.handleRealtimeStatusSync(parsed[1]);
                        } else if (parsed[0] === 'real_violation_history') {
                            // M14: 订阅时回送的历史事件
                            if (parsed[1] && parsed[1].events) {
                                parsed[1].events.forEach(e => this.addViolationAnnotation(e));
                            }
                            if (parsed[1] && parsed[1].violation_type_counts) {
                                this.todayCounts = parsed[1].violation_type_counts;
                                this.updateDashboardUI();
                            }
                        } else if (parsed[0] === 'connected') {
                            console.log('[WebSocket] 服务端确认连接');
                            // M14: 连接成功后订阅真实违规事件
                            this.socket.send('42["subscribe_real_violations"]');
                        }
                    }
                } catch (e) {
                    console.error('[WebSocket] 解析消息失败:', e);
                }
            };
            
            this.socket.onerror = (error) => {
                console.error('[WebSocket] 连接错误:', error);
                this.socketConnected = false;
                this.updateConnectionStatus(false);
            };
            
            this.socket.onclose = (event) => {
                console.log('[WebSocket] 连接关闭:', event.code, event.reason);
                this.socketConnected = false;
                this.updateConnectionStatus(false);
                
                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = this.reconnectDelay * Math.pow(2, Math.min(this.reconnectAttempts, 5));
                    console.log(`[WebSocket] 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，延迟 ${delay}ms`);
                    setTimeout(connect, delay);
                } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    console.log('[WebSocket] 重连失败，切换到本地模拟模式');
                    this.reconnectAttempts = 0;
                }
            };
        };
        
        setTimeout(connect, 1000);
    }
    
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            statusEl.className = connected ? 'status online' : 'status offline';
            statusEl.textContent = connected ? '已连接' : '连接断开';
        }
    }
    
    handleTrafficUpdate(data) {
        const now = Date.now();
        if (now - this.lastDataUpdate < this.dataUpdateInterval) {
            return;
        }
        this.lastDataUpdate = now;
        
        if (data.vehicles) {
            data.vehicles.forEach(v => {
                let existing = this.vehicles.find(veh => veh.id === v.id);
                if (existing) {
                    existing.mesh.position.set(v.x || v.position?.x || existing.mesh.position.x, 
                                           v.y || v.position?.y || 0.6, 
                                           v.z || v.position?.z || existing.mesh.position.z);
                    if (v.direction) {
                        existing.direction = new THREE.Vector3(v.direction.x, 0, v.direction.z).normalize();
                        existing.mesh.rotation.y = Math.atan2(-existing.direction.x, -existing.direction.z);
                    }
                    if (v.violation_type) {
                        existing.violation = v.violation_type;
                        const color = this.vehicleColors[v.violation_type] || this.vehicleColors.normal;
                        existing.mesh.material.color.setHex(color);
                    }
                } else {
                    this.addSimulatedVehicle({
                        id: v.id,
                        type: v.type || 'car',
                        x: v.x || v.position?.x || 0,
                        y: v.y || v.position?.y || 0.6,
                        z: v.z || v.position?.z || 0,
                        dx: v.dx || v.direction?.x || 0,
                        dz: v.dz || v.direction?.z || 1,
                        speed: v.speed || 0,
                        violation_type: v.violation_type || null
                    });
                }
            });
            
            const serverIds = new Set(data.vehicles.map(v => v.id));
            this.vehicles = this.vehicles.filter(v => serverIds.has(v.id));
        }
        
        if (data.traffic_light) {
            this.trafficLights.forEach(tl => {
                tl.currentState = data.traffic_light;
            });
        }
    }
    
    disconnectWebSocket() {
        if (this.socket) {
            this.socket.close(1000, '主动断开');
            this.socket = null;
        }
        this.socketConnected = false;
        this.updateConnectionStatus(false);
    }
    
    startAnimation() {
        const animate = () => {
            requestAnimationFrame(animate);
            
            this.frameCount++;
            this.updateTrafficLights();
            this.updateViolationAnnotations();  // M14: 旋转箭头/球轨道/环
            
            if (!this.socketConnected) {
                this.vehicles.forEach(vehicle => {
                    const shouldStop = this.checkStopAtLight(vehicle) || this.checkCollision(vehicle);
                    
                    if (shouldStop) {
                        vehicle.speed = Math.max(0, vehicle.speed - 2);
                        vehicle.stoppedAtLight = true;
                    } else {
                        vehicle.speed = Math.min(vehicle.targetSpeed, vehicle.speed + 0.5);
                        vehicle.stoppedAtLight = false;
                    }
                    
                    const moveSpeed = vehicle.speed * 0.0015;
                    vehicle.mesh.position.add(vehicle.direction.clone().multiplyScalar(moveSpeed));
                    
                    vehicle.mesh.rotation.y = Math.atan2(-vehicle.direction.x, -vehicle.direction.z);
                    
                    if (Math.abs(vehicle.mesh.position.x) > 50 || Math.abs(vehicle.mesh.position.z) > 50) {
                        this.removeVehicle(vehicle.id);
                    }
                });
            }
            
            this.controls.update();
            this.renderer.render(this.scene, this.camera);
            // M14: CSS2DRenderer 渲染车牌标签
            if (this.labelRenderer) {
                this.labelRenderer.render(this.scene, this.camera);
            }
        };
        
        animate();
    }
    
    startDataSimulation() {
        const updateTime = () => {
            const now = new Date();
            document.getElementById('current-time').textContent = 
                now.toLocaleTimeString('zh-CN', { hour12: false });
        };
        
        updateTime();
        setInterval(updateTime, 1000);
        
        document.getElementById('connection-status').className = 'status online';
        document.getElementById('connection-status').textContent = '已连接';
    }
    
    addSimulatedVehicle(data) {
        const color = this.vehicleColors[data.violation_type] || this.vehicleColors.normal;
        const vehicle = this.createVehicle(data.id, data.type, {
            x: data.x,
            y: 0.6,
            z: data.z
        });
        
        vehicle.direction = new THREE.Vector3(data.dx, 0, data.dz).normalize();
        vehicle.speed = data.speed;
        vehicle.violation = data.violation_type;
        
        this.vehicles.push(vehicle);
    }
    
    getVehicleCount() {
        return this.vehicles.length;
    }
    
    getViolationCount() {
        return this.vehicles.filter(v => v.violation !== null).length;
    }
    
    flashCamera(cameraId, duration = 3000) {
        const cam = this.cameras.find(c => c.id === cameraId);
        if (!cam) return;
        
        const cameraMesh = cam.mesh || null;
        const originalColor = cameraMesh ? cameraMesh.material.color.getHex() : null;
        
        let flashCount = 0;
        const maxFlashes = Math.floor(duration / 300);
        const flashInterval = setInterval(() => {
            flashCount++;
            if (flashCount >= maxFlashes) {
                clearInterval(flashInterval);
                if (cameraMesh && originalColor !== null) {
                    cameraMesh.material.color.setHex(originalColor);
                }
                cam.status = 'normal';
                this.updateCameraStatusIndicator(cameraId, 'normal');
                return;
            }
            
            if (flashCount % 2 === 0) {
                this.updateCameraStatusIndicator(cameraId, 'violation');
            } else {
                this.updateCameraStatusIndicator(cameraId, 'consulting');
            }
        }, 300);
    }
    
    updateCameraStatusIndicator(cameraId, status) {
        const cam = this.cameras.find(c => c.id === cameraId);
        if (!cam || !cam.statusLight) return;
        
        const colors = {
            normal: 0x4CAF50,
            consulting: 0xFFC107,
            violation: 0xF44336
        };
        
        cam.statusLight.material.color.setHex(colors[status] || colors.normal);
        cam.statusLight.material.emissive.setHex(colors[status] || colors.normal);
        cam.status = status;
    }
    
    highlightViolationVehicle(vehicleId) {
        const vehicle = this.vehicles.find(v => v.id === vehicleId);
        if (!vehicle) return;
        
        const edges = new THREE.EdgesGeometry(vehicle.mesh.geometry);
        const edgeMaterial = new THREE.LineBasicMaterial({ 
            color: 0xFF0000, 
            linewidth: 3 
        });
        const wireframe = new THREE.LineSegments(edges, edgeMaterial);
        wireframe.position.copy(vehicle.mesh.position);
        wireframe.rotation.copy(vehicle.mesh.rotation);
        
        if (vehicle.highlightMesh) {
            this.scene.remove(vehicle.highlightMesh);
        }
        
        vehicle.highlightMesh = wireframe;
        this.scene.add(wireframe);
        
        let pulseTime = 0;
        const pulseAnimation = () => {
            pulseTime += 0.05;
            if (pulseTime > Math.PI * 4) {
                return;
            }
            const scale = 1 + Math.sin(pulseTime) * 0.1;
            wireframe.scale.setScalar(scale);
            requestAnimationFrame(pulseAnimation);
        };
        pulseAnimation();
    }
    
    showViolationNotification(violationData) {
        const container = document.getElementById('notification-container') || this.createNotificationContainer();
        
        const notification = document.createElement('div');
        notification.className = 'violation-notification';
        notification.innerHTML = `
            <div class="notification-header">
                <span class="notification-icon">⚠️</span>
                <span class="notification-title">违规事件</span>
                <span class="notification-time">${new Date().toLocaleTimeString('zh-CN', {hour12: false})}</span>
            </div>
            <div class="notification-body">
                <div class="notification-type">${this.getViolationTypeName(violationData.violation_type)}</div>
                <div class="notification-detail">摄像头: ${violationData.camera_id || '未知'}</div>
                <div class="notification-confidence">置信度: ${((violationData.confidence || 0) * 100).toFixed(1)}%</div>
            </div>
        `;
        
        container.appendChild(notification);
        
        setTimeout(() => notification.classList.add('show'), 10);
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
        
        this.addViolationToTimeline(violationData);
    }
    
    createNotificationContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    addViolationToTimeline(violationData) {
        let timeline = document.getElementById('violation-timeline');
        if (!timeline) {
            timeline = document.createElement('div');
            timeline.id = 'violation-timeline';
            timeline.className = 'violation-timeline';
            timeline.innerHTML = '<div class="timeline-header">最近违规事件</div><div class="timeline-items"></div>';
            document.body.appendChild(timeline);
        }
        
        const itemsContainer = timeline.querySelector('.timeline-items');
        const item = document.createElement('div');
        item.className = 'violation-timeline-item';
        item.innerHTML = `
            <span class="timeline-item-time">${new Date().toLocaleTimeString('zh-CN', {hour12: false})}</span>
            <span class="timeline-item-type">${this.getViolationTypeName(violationData.violation_type)}</span>
            <span class="timeline-item-camera">${violationData.camera_id || ''}</span>
        `;
        
        itemsContainer.insertBefore(item, itemsContainer.firstChild);
        
        while (itemsContainer.children.length > 10) {
            itemsContainer.removeChild(itemsContainer.lastChild);
        }
    }
    
    getViolationTypeName(type) {
        const names = {
            'red_light': '闯红灯',
            'no_helmet': '未戴头盔',
            'wrong_way': '逆行',
            'illegal_parking': '违规停车',
            'lane_departure': '压线行驶',
            'speeding': '超速'
        };
        return names[type] || type || '未知违规';
    }
    
    setupMultiCameraStatus() {
        this.cameras.forEach(cam => {
            if (cam.statusLight) return;
            
            const lightGeo = new THREE.SphereGeometry(0.25, 16, 16);
            const lightMat = new THREE.MeshStandardMaterial({
                color: 0x4CAF50,
                emissive: 0x4CAF50,
                emissiveIntensity: 0.8
            });
            const statusLight = new THREE.Mesh(lightGeo, lightMat);
            statusLight.position.copy(cam.position);
            statusLight.position.y = 4.2;
            this.scene.add(statusLight);
            
            cam.statusLight = statusLight;
            cam.status = 'normal';
            
            const lineGeo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(cam.position.x, 4.2, cam.position.z),
                new THREE.Vector3(0, 8, 0)
            ]);
            const lineMat = new THREE.LineDashedMaterial({
                color: 0x2196F3,
                dashSize: 1,
                gapSize: 0.5,
                transparent: true,
                opacity: 0.3
            });
            const dataLine = new THREE.Line(lineGeo, lineMat);
            dataLine.computeLineDistances();
            this.scene.add(dataLine);
            cam.dataLine = dataLine;
        });
    }
    
    triggerViolationEvent(eventData) {
        if (eventData.camera_id) {
            this.flashCamera(eventData.camera_id, 3000);
        }
        
        if (eventData.vehicle_id) {
            this.highlightViolationVehicle(eventData.vehicle_id);
        }
        
        this.showViolationNotification(eventData);
    }
    
    createVideoPanel() {
        let panel = document.getElementById('video-monitor-panel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'video-monitor-panel';
            panel.className = 'video-monitor-panel';
            panel.innerHTML = `
                <div class="video-panel-header">
                    <span class="video-panel-title">📹 实时监控</span>
                    <select class="camera-selector" id="video-camera-select">
                        <option value="">选择摄像头</option>
                    </select>
                    <button class="minimize-btn" id="minimize-video-panel">−</button>
                    <button class="close-btn" id="close-video-panel">✕</button>
                </div>
                <div class="video-panel-body" id="video-panel-body">
                    <img id="video-feed-img" class="video-feed" src="" alt="视频流" />
                    <div class="video-placeholder" id="video-placeholder">
                        <span>📷</span>
                        <p>选择摄像头查看实时画面</p>
                    </div>
                </div>
                <div class="video-panel-info" id="video-panel-info">
                    <div class="info-item"><span>状态:</span><span class="status-text" id="video-status">离线</span></div>
                    <div class="info-item"><span>FPS:</span><span id="video-fps">0</span></div>
                    <div class="info-item"><span>帧数:</span><span id="video-frames">0</span></div>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('video-camera-select').addEventListener('change', (e) => {
                this.selectVideoCamera(parseInt(e.target.value));
            });
            
            document.getElementById('close-video-panel').addEventListener('click', () => {
                this.closeVideoPanel();
            });
            
            document.getElementById('minimize-video-panel').addEventListener('click', () => {
                this.toggleVideoPanelMinimize();
            });
            
            this.makeVideoPanelDraggable(panel);
            this.fetchCameraList();
        }
    }
    
    async fetchCameraList() {
        try {
            const response = await fetch(`${BACKEND_URL}/api/realtime/camera/list`);
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.cameras) {
                    const select = document.getElementById('video-camera-select');
                    select.innerHTML = '<option value="">选择摄像头</option>';
                    data.cameras.forEach(cam => {
                        if (cam.available) {
                            const option = document.createElement('option');
                            option.value = cam.index;
                            option.textContent = `摄像头 ${cam.index}`;
                            select.appendChild(option);
                        }
                    });
                }
            }
        } catch (e) {
            console.error('获取摄像头列表失败:', e);
        }
    }
    
    makeVideoPanelDraggable(panel) {
        const header = panel.querySelector('.video-panel-header');
        let isDragging = false;
        let startX, startY, panelX, panelY;
        
        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            panelX = panel.offsetLeft;
            panelY = panel.offsetTop;
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
        
        const onMouseMove = (e) => {
            if (!isDragging) return;
            
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            
            let newX = panelX + dx;
            let newY = panelY + dy;
            
            const maxX = window.innerWidth - panel.offsetWidth;
            const maxY = window.innerHeight - panel.offsetHeight;
            
            newX = Math.max(0, Math.min(newX, maxX));
            newY = Math.max(0, Math.min(newY, maxY));
            
            panel.style.left = newX + 'px';
            panel.style.top = newY + 'px';
        };
        
        const onMouseUp = () => {
            isDragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }
    
    toggleVideoPanelMinimize() {
        this.isVideoMinimized = !this.isVideoMinimized;
        const body = document.getElementById('video-panel-body');
        const info = document.getElementById('video-panel-info');
        const btn = document.getElementById('minimize-video-panel');
        
        if (this.isVideoMinimized) {
            body.style.display = 'none';
            info.style.display = 'none';
            btn.textContent = '+';
        } else {
            body.style.display = 'block';
            info.style.display = 'flex';
            btn.textContent = '−';
        }
    }
    
    async selectVideoCamera(cameraIndex) {
        if (isNaN(cameraIndex)) {
            await this.stopVideoDetection();
            this.activeVideoCamera = null;
            document.getElementById('video-feed-img').src = '';
            document.getElementById('video-feed-img').style.display = 'none';
            document.getElementById('video-placeholder').style.display = 'flex';
            document.getElementById('video-status').textContent = '离线';
            document.getElementById('video-status').className = 'status-text';
            return;
        }
        
        this.activeVideoCamera = cameraIndex;
        document.getElementById('video-monitor-panel').style.display = 'block';
        document.getElementById('video-feed-img').style.display = 'none';
        document.getElementById('video-placeholder').style.display = 'flex';
        document.getElementById('video-status').textContent = '启动中...';
        document.getElementById('video-status').className = 'status-text connecting';
        
        try {
            const response = await fetch(`${BACKEND_URL}/api/realtime/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ camera_index: cameraIndex })
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    const videoUrl = `${BACKEND_URL}/api/realtime/stream?t=${Date.now()}`;
                    document.getElementById('video-feed-img').src = videoUrl;
                    document.getElementById('video-feed-img').style.display = 'block';
                    document.getElementById('video-placeholder').style.display = 'none';
                    document.getElementById('video-status').textContent = '在线';
                    document.getElementById('video-status').className = 'status-text online';
                } else {
                    throw new Error(result.message || '启动失败');
                }
            } else {
                throw new Error('启动请求失败');
            }
        } catch (e) {
            console.error('启动摄像头失败:', e);
            document.getElementById('video-status').textContent = '启动失败';
            document.getElementById('video-status').className = 'status-text';
            this.activeVideoCamera = null;
        }
    }
    
    async closeVideoPanel() {
        await this.stopVideoDetection();
        document.getElementById('video-monitor-panel').style.display = 'none';
        this.activeVideoCamera = null;
        this.isVideoMinimized = false;
    }
    
    async stopVideoDetection() {
        try {
            await fetch(`${BACKEND_URL}/api/realtime/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (e) {
            console.error('停止检测失败:', e);
        }
        document.getElementById('video-feed-img').src = '';
    }
    
    startVideoStreamListener() {
        setInterval(async () => {
            if (!this.activeVideoCamera) return;
            
            try {
                const response = await fetch(`${BACKEND_URL}/api/realtime/status`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.data) {
                        document.getElementById('video-fps').textContent = data.data.current_fps ? data.data.current_fps.toFixed(1) : '0';
                        document.getElementById('video-frames').textContent = data.data.total_frames || '0';
                    }
                }
            } catch (e) {
                console.error('获取视频状态失败:', e);
            }
        }, 2000);
    }
    
    quickViewCamera(cameraId) {
        this.selectVideoCamera(cameraId);
        this.setCameraView(cameraId);
    }
    
    // ==================================================================
    // M14: 数字孪生真实数据联动
    // ==================================================================
    
    /**
     * M14: 创建 CSS2DRenderer 用于在 3D 场景中渲染车牌标签
     */
    createLabelRenderer() {
        const container = document.getElementById('scene-container');
        this.labelRenderer = new CSS2DRenderer();
        this.labelRenderer.setSize(container.clientWidth, container.clientHeight);
        this.labelRenderer.domElement.style.position = 'absolute';
        this.labelRenderer.domElement.style.top = '0';
        this.labelRenderer.domElement.style.pointerEvents = 'none';
        this.labelRenderer.domElement.style.zIndex = '5';
        container.appendChild(this.labelRenderer.domElement);
    }
    
    /**
     * M14: 添加违规标注（红色旋转箭头 + 车牌+违规类型卡片）
     * @param {Object} event - 后端推送的违规事件
     */
    addViolationAnnotation(event) {
        const trackId = event.track_id;
        const vtype = event.violation_type;
        const plate = event.plate_number || '未识别';
        const pos = event.position || { x: 0, y: 0.6, z: 0 };
        const color = VIOLATION_COLOR_MAP[vtype] || 0xFF0000;
        const colorHex = '#' + color.toString(16).padStart(6, '0');
        
        // 已存在则先移除
        this.removeViolationAnnotation(trackId);
        
        // 1) 红色旋转箭头组
        const arrowGroup = new THREE.Group();
        arrowGroup.position.set(pos.x, pos.y, pos.z);
        
        // 主箭头：圆锥指向下方
        const arrowGeo = new THREE.ConeGeometry(0.6, 1.8, 8);
        const arrowMat = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.8,
            metalness: 0.3,
            roughness: 0.5,
        });
        const arrow = new THREE.Mesh(arrowGeo, arrowMat);
        arrow.position.y = 3;
        arrow.rotation.x = Math.PI;  // 指向下方
        arrow.castShadow = true;
        arrowGroup.add(arrow);
        
        // 环绕的小球（3 个，绕主箭头旋转）
        for (let i = 0; i < 3; i++) {
            const ballGeo = new THREE.SphereGeometry(0.25, 12, 12);
            const ballMat = new THREE.MeshStandardMaterial({
                color: color,
                emissive: color,
                emissiveIntensity: 0.6,
            });
            const ball = new THREE.Mesh(ballGeo, ballMat);
            ball.userData.orbitRadius = 1.5 + i * 0.3;
            ball.userData.orbitSpeed = 0.04 + i * 0.01;
            ball.userData.orbitPhase = (i / 3) * Math.PI * 2;
            ball.userData.orbitHeight = 2.5 + Math.sin(i) * 0.5;
            arrowGroup.add(ball);
        }
        
        // 旋转环
        const ringGeo = new THREE.TorusGeometry(1.2, 0.08, 8, 32);
        const ringMat = new THREE.MeshStandardMaterial({
            color: color,
            emissive: color,
            emissiveIntensity: 0.7,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.y = 0.5;
        arrowGroup.add(ring);
        arrowGroup.userData.ring = ring;
        
        this.scene.add(arrowGroup);
        
        // 2) CSS2D 车牌+违规类型卡片
        const labelDiv = document.createElement('div');
        labelDiv.className = 'violation-label-card';
        labelDiv.style.borderColor = colorHex;
        labelDiv.innerHTML = `
            <div class="vlc-type" style="background:${colorHex}">${VIOLATION_NAME_CN[vtype] || vtype}</div>
            <div class="vlc-plate">${plate}</div>
            <div class="vlc-conf">置信度 ${(event.confidence * 100).toFixed(0)}%</div>
        `;
        const label = new CSS2DObject(labelDiv);
        label.position.set(pos.x, pos.y + 4.5, pos.z);
        this.scene.add(label);
        
        this.violationAnnotations.set(trackId, {
            arrowGroup,
            label,
            labelDiv,
            expireAt: Date.now() + 15000,  // 15 秒后自动消失
            createdAt: Date.now(),
            color,
        });
        
        // 3) 同步仪表盘计数（来自事件源）
        if (this.todayCounts[vtype] !== undefined) {
            this.todayCounts[vtype] = (this.todayCounts[vtype] || 0) + 1;
            this.updateDashboardUI();
        }
        
        console.log(`[M14] 新增违规标注 track_id=${trackId} type=${vtype} plate=${plate}`);
    }
    
    /**
     * M14: 移除指定 track_id 的违规标注
     */
    removeViolationAnnotation(trackId) {
        const ann = this.violationAnnotations.get(trackId);
        if (!ann) return;
        this.scene.remove(ann.arrowGroup);
        this.scene.remove(ann.label);
        if (ann.labelDiv && ann.labelDiv.parentNode) {
            ann.labelDiv.parentNode.removeChild(ann.labelDiv);
        }
        // 释放几何/材质
        ann.arrowGroup.traverse(obj => {
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) obj.material.dispose();
        });
        this.violationAnnotations.delete(trackId);
    }
    
    /**
     * M14: 标注过期清理循环 - 15 秒后淡出消失
     */
    startAnnotationExpiry() {
        setInterval(() => {
            const now = Date.now();
            for (const [tid, ann] of this.violationAnnotations.entries()) {
                const age = now - ann.createdAt;
                if (now > ann.expireAt) {
                    this.removeViolationAnnotation(tid);
                } else if (age > 12000) {
                    // 最后 3 秒淡出
                    const fadeRatio = Math.max(0, (ann.expireAt - now) / 3000);
                    ann.labelDiv.style.opacity = fadeRatio.toString();
                    ann.arrowGroup.children.forEach(c => {
                        if (c.material) {
                            c.material.transparent = true;
                            c.material.opacity = fadeRatio;
                        }
                    });
                }
            }
        }, 500);
    }
    
    /**
     * M14: 每帧更新违规标注（旋转箭头、球轨道、环旋转）
     */
    updateViolationAnnotations() {
        const t = this.frameCount * 0.05;
        for (const ann of this.violationAnnotations.values()) {
            // 主箭头上下浮动
            const arrow = ann.arrowGroup.children[0];
            arrow.position.y = 3 + Math.sin(t * 0.5) * 0.3;
            // 球轨道
            for (let i = 1; i <= 3; i++) {
                const ball = ann.arrowGroup.children[i];
                if (!ball || !ball.userData.orbitRadius) continue;
                const angle = t * ball.userData.orbitSpeed + ball.userData.orbitPhase;
                ball.position.x = Math.cos(angle) * ball.userData.orbitRadius;
                ball.position.z = Math.sin(angle) * ball.userData.orbitRadius;
                ball.position.y = ball.userData.orbitHeight + Math.sin(t * 0.7 + i) * 0.3;
            }
            // 环旋转
            if (ann.arrowGroup.userData.ring) {
                ann.arrowGroup.userData.ring.rotation.z += 0.02;
            }
        }
    }
    
    /**
     * M14: 仪表盘同步 - 从 /api/dashboard/today-stats 拉取真实计数
     */
    startDashboardSync() {
        const sync = async () => {
            try {
                const resp = await fetch('/api/dashboard/today-stats');
                if (resp.ok) {
                    const data = await resp.json();
                    if (data.success && data.today_counts) {
                        // 用后端真实计数覆盖本地（避免本地演示事件导致重复）
                        this.todayCounts = data.today_counts;
                        this.updateDashboardUI();
                    }
                }
            } catch (e) {
                console.warn('[M14] 仪表盘同步失败:', e);
            }
        };
        sync();
        setInterval(sync, 3000);
    }
    
    /**
     * M14: 更新仪表盘 UI - 今日逆行/未戴头盔/闯红灯/违停数
     */
    updateDashboardUI() {
        const update = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        update('stat-wrong-way', this.todayCounts.wrong_way || 0);
        update('stat-no-helmet', this.todayCounts.no_helmet || 0);
        update('stat-red-light', this.todayCounts.red_light || 0);
        update('stat-illegal-parking', this.todayCounts.illegal_parking || 0);
    }
    
    /**
     * M14: 演示按钮 - 调用后端 /api/demo/trigger-scene
     */
    async triggerDemoScene(sceneType) {
        try {
            const resp = await fetch('/api/demo/trigger-scene', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scene_type: sceneType }),
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data.success) {
                    console.log(`[M14] 演示场景触发成功: ${data.violation_type_cn} - ${data.event.plate_number}`);
                    // 事件会通过 WebSocket real_violation_event 推送，本地无需手动添加
                    return data;
                }
            }
        } catch (e) {
            console.error('[M14] 演示场景触发失败:', e);
        }
        return null;
    }
    
    /**
     * M14: 接收后端推送的真实违规事件
     */
    handleRealViolationEvent(event) {
        if (!event || !event.track_id) return;
        this.addViolationAnnotation(event);
        // 显示通知
        this.showViolationNotification({
            violation_type: event.violation_type,
            camera_id: `track_${event.track_id}`,
            confidence: event.confidence,
            plate: event.plate_number,
        });
    }
    
    /**
     * M14: 接收后端推送的实时状态同步（更新仪表盘辅助信息）
     */
    handleRealtimeStatusSync(status) {
        const update = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        update('stat-avg-fps', (status.avg_fps || 0).toFixed(1));
        update('stat-processed-frames', status.processed_frames || 0);
        update('stat-confirmed-count', status.confirmed_count || 0);
        update('stat-pending-count', status.pending_count || 0);
    }
}

let trafficScene;

export function initScene() {
    trafficScene = new TrafficScene();
    return trafficScene;
}

export function getScene() {
    return trafficScene;
}
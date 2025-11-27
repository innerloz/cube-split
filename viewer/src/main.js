import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import GUI from 'lil-gui';

// Scene setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 2.0; // Default, will be updated

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

// Environment Map (Important for PBR materials)
const pmremGenerator = new THREE.PMREMGenerator(renderer);
scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;

// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// Lights
const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
directionalLight.position.set(5, 5, 5);
scene.add(directionalLight);

const directionalLight2 = new THREE.DirectionalLight(0xffffff, 1);
directionalLight2.position.set(-5, -5, -5);
scene.add(directionalLight2);

// UI
const gui = new GUI();
const globalSettings = {
    unifiedLook: false,
    unifiedColor: 0xffffff,
    model: 'nifti.glb' // Default model
};

// Model loading management
let currentModel = null;
const loader = new GLTFLoader();

function loadModel(modelPath) {
    if (currentModel) {
        scene.remove(currentModel);
        // Clean up GUI
        gui.folders.forEach(f => {
            if (f._title !== 'Global Settings' && f._title !== 'Model Selection') {
                f.destroy();
            }
        });
        currentModel = null;
    }

    loader.load(
      `/${modelPath}`,
      (gltf) => {
        const model = gltf.scene;
        currentModel = model;
        const allMeshes = [];
        
        // Traverse and colorize
        let colorIndex = 0;
        const colors = [
          0xff0000, 0x00ff00, 0x0000ff, 0xffff00, 
          0xff00ff, 0x00ffff, 0xff8800, 0x8800ff
        ];

        model.traverse((child) => {
          if (child.isMesh) {
            const color = colors[colorIndex % colors.length];
            
            // Store original color
            child.userData.originalColor = color;

            // Debug Attributes
            console.log(`Mesh ${child.name} attributes:`, Object.keys(child.geometry.attributes));
            
            // 1. Remove Vertex Colors if present (fixes black mesh issue)
            if (child.geometry.attributes.color) {
                console.log(`Removing vertex colors from ${child.name}`);
                child.geometry.deleteAttribute('color');
            }

            // 2. Ensure Normals exist
            if (!child.geometry.attributes.normal) {
                console.warn(`Mesh ${child.name} has NO normals. Computing...`);
                child.geometry.computeVertexNormals();
            }

            // Apply Unified Look if active
            const displayColor = globalSettings.unifiedLook ? globalSettings.unifiedColor : color;

            child.material = new THREE.MeshPhysicalMaterial({
              color: displayColor,
              roughness: 0.3,       
              metalness: 0.0,       
              clearcoat: 0.5,
              clearcoatRoughness: 0.1,
              reflectivity: 0.5,
              transmission: 0.0,
              side: THREE.DoubleSide,
              transparent: true,
              opacity: 1.0,
              flatShading: false,
              vertexColors: false   
            });
            
            allMeshes.push(child);
            
            // Initialize settings for this mesh
            const name = child.name || `Region ${colorIndex}`;
            
            const folder = gui.addFolder(name);
            const settings = { visible: true, opacity: 1.0 };
            
            folder.add(settings, 'visible').onChange((v) => {
                child.visible = v;
            });
            folder.add(settings, 'opacity', 0, 1).onChange((v) => {
                child.material.opacity = v;
                child.material.needsUpdate = true; 
            });

            colorIndex++;
          }
        });

        // Center the model and Fit Camera
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        model.position.sub(center);

        scene.add(model);
        
        console.log("Model loaded. Size:", size);
        console.log("Mesh Count:", allMeshes.length);

        // Auto-fit Camera to Model
        const maxDim = Math.max(size.x, size.y, size.z);
        if (maxDim > 0) {
            const fov = camera.fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / (2 * Math.tan(fov / 2)));
            cameraZ *= 2.5; 
            
            camera.position.set(0, 0, cameraZ);
            camera.far = Math.max(1000, cameraZ * 10);
            camera.updateProjectionMatrix();
            
            controls.target.set(0, 0, 0);
            controls.update();
            
            console.log("Auto-fit camera to Z:", cameraZ);
        }
        
        // Store meshes for global updates
        scene.userData.allMeshes = allMeshes;
      },
      (xhr) => {
        console.log((xhr.loaded / xhr.total * 100) + '% loaded');
      },
      (error) => {
        console.error('An error happened', error);
      }
    );
}

// Initial Load
loadModel('nifti.glb');

// GUI Setup
const modelFolder = gui.addFolder('Model Selection');
modelFolder.add(globalSettings, 'model', ['sphere.glb', 'cylinder.glb', 'prism.glb', 'nifti.glb']).name('Geometry').onChange((value) => {
    loadModel(value);
});

const globalFolder = gui.addFolder('Global Settings');
globalFolder.add(globalSettings, 'unifiedLook').name('Unified Look').onChange((value) => {
    if (scene.userData.allMeshes) {
        scene.userData.allMeshes.forEach(mesh => {
            if (value) {
                mesh.material.color.setHex(globalSettings.unifiedColor);
            } else {
                mesh.material.color.setHex(mesh.userData.originalColor);
            }
        });
    }
});
globalFolder.addColor(globalSettings, 'unifiedColor').name('Unified Color').onChange((value) => {
    if (globalSettings.unifiedLook && scene.userData.allMeshes) {
        scene.userData.allMeshes.forEach(mesh => {
            mesh.material.color.setHex(value);
        });
    }
});


// Animation Loop
function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}

animate();

// Resize Handler
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

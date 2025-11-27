import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import GUI from 'lil-gui';

// Scene setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111111);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 4.0; // Zoomed out a bit

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
const regionSettings = {};

// Model loading management
let currentModel = null;
const loader = new GLTFLoader();

function loadModel(modelPath) {
    if (currentModel) {
        scene.remove(currentModel);
        // Clean up GUI
        for (const key in regionSettings) {
            // Need to find and remove folders. 
            // lil-gui doesn't make this super easy without tracking folders.
            // We'll just destroy and recreate the GUI or folders.
        }
        // Simpler: reset GUI completely if possible, or just manage folders better.
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
            // We don't persist region settings across model loads for simplicity
            
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

        // Center the model
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        model.position.sub(center);

        scene.add(model);
        
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

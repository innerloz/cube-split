# Spherical Regions Meshing Demo

This project demonstrates generating a segmented spherical mesh using Python and visualizing it with Three.js.

## Project Structure

- `generator/`: Python scripts for voxel generation, Voronoi partitioning, and meshing.
- `viewer/`: Vite + Three.js web application for viewing the result.

## Prerequisites

- Python 3.8+ (Python 3.12 recommended)
- Node.js (v16+)
- `pip` and `npm`

## Instructions

### 1. Generate the Mesh

First, install the Python dependencies and run the generation script. It uses a virtual environment to manage dependencies.

```bash
# Navigate to the generator directory (optional, commands below assume root)
# Create and activate virtual environment (if not already done)
python3.12 -m venv generator/venv
source generator/venv/bin/activate

# Install dependencies
pip install -r generator/requirements.txt

# Run the generation script
python generator/generate.py
```

This will generate a `model.glb` file in `viewer/public/`.

### 2. Run the Web Viewer

Next, verify the result in the web viewer.

```bash
# Navigate to the viewer directory
cd viewer

# Install dependencies
npm install

# Start the development server
npm run dev
```

Open the URL provided by Vite (usually `http://localhost:5173`) in your browser.

## Features

- **Procedural Generation**: Creates a sphere and splits it into 8 random Voronoi regions.
- **Meshing**: Uses Marching Cubes to generate a mesh for each region.
- **Export**: Saves the scene as a GLTF binary (.glb).
- **Visualization**: Renders the regions with different colors in a browser with interactive controls (rotate, zoom, pan).


# Streetview-panorama-scraping

Scrape Google Street View panoramas for a given area.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Edit `config.yaml` to set your desired center coordinates, radius, and resolution.

2. Run the three steps:

```bash
# Step 1: Get panorama IDs (opens map in browser)
python 1_get_panoid_info.py

# Step 2: Download panorama images
python 2_download_panoramas.py

# Step 3: Project to cube faces
python 3_project_panoramas.py
```

## Output

- `panoramas/` - Raw equirectangular panorama images
- `cube_pano/` - Projected cube face images (front, back, left, right)
- `Result.html` - Map showing panorama locations

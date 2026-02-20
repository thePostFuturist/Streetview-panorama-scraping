import asyncio
import json
import os
import traceback
import glob
import aiohttp

import streetview


async def download_tiles_async(tiles, directory, session):
    """ Downloads all the tiles in a Google Street View panorama into a directory. """

    for i, (x, y, fname, url) in enumerate(tiles):
        # Try to download the image file
        url = url.replace("http://", "https://")
        retries = 3
        for attempt in range(retries):
            try:
                async with session.get(url) as response:
                    if response.status == 400 or response.status == 429:
                        if attempt < retries - 1:
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        print(f"Warning: HTTP {response.status} for tile {fname}")
                        break
                    if response.status != 200:
                        print(f"Warning: HTTP {response.status} for tile {fname}")
                        break
                    content = await response.read()
                    # Validate JPEG magic bytes
                    if not content.startswith(b'\xff\xd8\xff'):
                        print(f"Warning: Invalid image data for tile {fname}")
                        break
                    with open(directory + '/' + fname, 'wb') as out_file:
                        out_file.write(content)
                    break
            except Exception as e:
                print(f"Error downloading tile {fname}: {e}")
                break


async def download_panorama(panoid,
                            session=None,
                            tile_diretory='tiles',
                            pano_directory='panoramas'):
    """ 
    Downloads a panorama from latitude and longitude
    Heavily IO bound (~98%), ~40s per panorama without using asyncio.
    """
    if not os.path.isdir(tile_diretory):
        os.makedirs(tile_diretory)
    if not os.path.isdir(pano_directory):
        os.makedirs(pano_directory)

    try:
        x = streetview.tiles_info(panoid['panoid'])
        await download_tiles_async(x, tile_diretory, session)
        streetview.stich_tiles(panoid['panoid'],
                               x,
                               tile_diretory,
                               pano_directory,
                               point=(panoid['lat'], panoid['lon']))
        streetview.delete_tiles(x, tile_diretory)

    except:
        print(f'Failed to create panorama\n{traceback.format_exc()}')


def panoid_created(panoid):
    """ Checks if the panorama was already created """
    file = f"{panoid['lat']}_{panoid['lon']}_{panoid['panoid']}.jpg"
    return os.path.isfile(os.path.join('panoramas', file))


async def download_loop(panoids, pmax):
    """ Main download loop """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/maps',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    }
    conn = aiohttp.TCPConnector(limit=20)  # Reduced from 100 to avoid rate limiting
    async with aiohttp.ClientSession(connector=conn,
                                     headers=headers,
                                     auto_decompress=False) as session:
        try:
            await asyncio.gather(*[
                download_panorama(panoid, session=session)
                for panoid in panoids[:pmax] if not panoid_created(panoid)
            ])
        except:
            print(traceback.format_exc())


if __name__ == "__main__":
    # Load panoids info - check for indoor file first, then outdoor pattern
    json_files = glob.glob('indoor_panoids.json') + glob.glob('panoids*.json')

    if not json_files:
        print('No panoids file found (indoor_panoids.json or panoids_*.json)')
        exit()
    elif len(json_files) > 1:
        print(f'Multiple panoids files found: {json_files}')
        print('Please specify which to use or remove extras')
        exit()

    panoids_file = json_files[0]
    print(f"Using: {panoids_file}")

    with open(panoids_file, 'r') as f:
        panoids = json.load(f)

    # Filter out non-standard panoids (CIHM prefix = custom imagery that doesn't work with cbk0 API)
    original_count = len(panoids)
    panoids = [p for p in panoids if not p['panoid'].startswith('CIHM')]
    if len(panoids) < original_count:
        print(f"Filtered out {original_count - len(panoids)} non-standard panoids (CIHM custom imagery)")

    print(f"Loaded {len(panoids)} panoids")

    # Download panorama in batches of 100
    loop = asyncio.get_event_loop()
    i = 0
    while True:
        i += 1
        print(f'Running the next batch: {(i-1)*100+1} -> {i*100}')
        loop.run_until_complete(download_loop(panoids, 100 * i))
        if 100 * i > len(panoids):
            break

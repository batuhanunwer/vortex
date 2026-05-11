import glob
import sqlite3
import re
import urllib.request

# 1. Fetch background image from wiki
bg_image_url = ""
try:
    req = urllib.request.Request('https://wiki.knglrp.com', headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    html = response.read().decode('utf-8')
    # Find something that looks like an image background, or maybe an img tag with class background
    # Usually it's in a <style> tag or CSS, or an <img> tag.
    # We will just supply a placeholder or the exact one if we find it.
    match = re.search(r'(https?://[^\s\"\']+\.(?:png|jpg|jpeg|webp))', html)
    if match:
        bg_image_url = match.group(1)
except Exception as e:
    print(f"Failed to fetch wiki bg: {e}")

# If we couldn't confidently find the exact bg image, let's just use CSS. The user wants the background. 
# In the screenshot it looked like a city. Let's explicitly just search the HTML for any relevant image or keep it elegant.
# For now let's just insert the bg_image_url if found.

# 2. Fix the templates (Revert fonts AND apply background)
for fp in glob.glob('templates/*.html'):
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    
    # Revert font
    c = c.replace("'Montserrat', 'Inter',", "'Inter',")
    
    # Apply background
    if bg_image_url:
        bg_css = f"background: url('{bg_image_url}') center center fixed; background-size: cover;"
        # Find where body background is set
        c = re.sub(r"background:\s*radial-gradient[^;]+;", bg_css, c)
        c = re.sub(r"background:\s*#03050B;", bg_css, c)
        c = re.sub(r"background:\s*#050A1A;", bg_css, c)

    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)

# 3. Create Admin account
conn = sqlite3.connect('users.db')
cursor = conn.cursor()
try:
    # default pass test logic
    cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('admin', 'admin', 'admin'))
    conn.commit()
except sqlite3.IntegrityError:
    cursor.execute('UPDATE users SET role=?, password=? WHERE username=?', ('admin', 'admin', 'admin'))
    conn.commit()
conn.close()

if bg_image_url:
    print(f"Done. Used bg image: {bg_image_url}")
else:
    print("Done. No bg image found.")

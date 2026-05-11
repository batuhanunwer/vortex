import glob

bg_css = "background-image: linear-gradient(rgba(11, 22, 59, 0.8), rgba(3, 5, 11, 0.98)), url('https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?q=80&w=2000&auto=format&fit=crop'); background-size: cover; background-attachment: fixed; background-position: center;"

for fp in glob.glob('templates/*.html'):
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    
    c = c.replace("background: radial-gradient(ellipse at top center, #0B163B 0%, #03050B 100%);", bg_css)
    c = c.replace("background: #03050B;", bg_css)
    c = c.replace("background: #050A1A;", bg_css)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c)

print("Background applied")

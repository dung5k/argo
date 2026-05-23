"""Build VSIX - packs extension.js, package.json, README.md, and node_modules recursively."""
import zipfile
import os
import json

ext_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(ext_dir, 'package.json'), 'r') as f:
    pkg = json.load(f)

version = pkg['version']
name = pkg['name']
vsix_name = f"{name}-{version}.vsix"
vsix_path = os.path.join(ext_dir, vsix_name)

content_types = '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension=".js" ContentType="application/javascript"/><Default Extension=".json" ContentType="application/json"/><Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>'

vsixmanifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{pkg['publisher']}"/>
    <DisplayName>{pkg['displayName']}</DisplayName>
    <Description>{pkg['description']}</Description>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/extension.js" Addressable="true"/>
  </Assets>
</PackageManifest>'''

if os.path.exists(vsix_path):
    os.remove(vsix_path)

print("Building VSIX package...")
with zipfile.ZipFile(vsix_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', content_types)
    z.writestr('extension.vsixmanifest', vsixmanifest)
    
    # Pack root files
    z.write(os.path.join(ext_dir, 'extension.js'), 'extension/extension.js')
    z.write(os.path.join(ext_dir, 'package.json'), 'extension/package.json')
    if os.path.exists(os.path.join(ext_dir, 'README.md')):
        z.write(os.path.join(ext_dir, 'README.md'), 'extension/README.md')
        
    # Pack node_modules recursively
    node_modules_path = os.path.join(ext_dir, 'node_modules')
    if os.path.exists(node_modules_path):
        for root, dirs, files in os.walk(node_modules_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ext_dir)
                archive_name = os.path.join('extension', rel_path).replace('\\', '/')
                z.write(full_path, archive_name)

print(f"VSIX {version} built successfully: {os.path.getsize(vsix_path)} bytes")

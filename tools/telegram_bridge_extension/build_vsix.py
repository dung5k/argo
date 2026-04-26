"""Build VSIX - dùng đúng manifest format từ bản 1.2.7 đang chạy tốt."""
import zipfile
import os
import json

ext_dir = r'd:\DungLA\client1\tools\telegram_bridge_extension'

with open(os.path.join(ext_dir, 'package.json'), 'r') as f:
    pkg = json.load(f)

version = pkg['version']
name = pkg['name']
vsix_name = f"{name}-{version}.vsix"
vsix_path = os.path.join(ext_dir, vsix_name)

# Sao chép y hệt format từ bản 1.2.7
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

with zipfile.ZipFile(vsix_path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', content_types)
    z.writestr('extension.vsixmanifest', vsixmanifest)
    z.write(os.path.join(ext_dir, 'extension.js'), 'extension/extension.js')
    z.write(os.path.join(ext_dir, 'package.json'), 'extension/package.json')

print(f"✅ VSIX {version} built: {os.path.getsize(vsix_path)} bytes")
with zipfile.ZipFile(vsix_path, 'r') as z:
    for info in z.infolist():
        print(f"  {info.filename} ({info.file_size})")

#!/bin/bash
# macOS app 构建脚本
# 运行前确保已安装依赖: pip3 install PyQt6 requests pyqtgraph akshare beautifulsoup4 pandas lxml

set -e
APP_NAME="实时外汇监控系统"
BUILD_DIR="dist/${APP_NAME}.app"

echo "=== 构建 ${APP_NAME} macOS 应用 ==="

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/Contents/MacOS" "$BUILD_DIR/Contents/Resources"

cp main.py config.py database.py calculator.py fetcher.py bank_fetcher.py requirements.txt forex_data.db "$BUILD_DIR/Contents/Resources/"
cp -r ui "$BUILD_DIR/Contents/Resources/ui/"

PYTHON=$(which python3)
cat > "$BUILD_DIR/Contents/MacOS/$APP_NAME" << PYEOF
#!/bin/bash
DIR="\$(cd "\$(dirname "\$0")/../Resources" && pwd)"
cd "\$DIR"
exec "$PYTHON" main.py "\$@"
PYEOF
chmod +x "$BUILD_DIR/Contents/MacOS/$APP_NAME"

cat > "$BUILD_DIR/Contents/Info.plist" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>$APP_NAME</string>
<key>CFBundleIdentifier</key><string>com.forex.monitor</string>
<key>CFBundleName</key><string>$APP_NAME</string>
<key>CFBundleDisplayName</key><string>$APP_NAME</string>
<key>CFBundleVersion</key><string>1.0.0</string>
<key>CFBundleShortVersionString</key><string>1.0.0</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>LSMinimumSystemVersion</key><string>10.15</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLISTEOF
printf 'APPL????' > "$BUILD_DIR/Contents/PkgInfo"

echo "✅ 构建完成: $BUILD_DIR"
echo ""
echo "复制到 /Applications:"
echo "  cp -r \"$BUILD_DIR\" /Applications/"
echo ""
echo "创建 DMG:"
echo "  hdiutil create -volname \"$APP_NAME\" -srcfolder \"$BUILD_DIR\" -ov -format UDZO \"dist/${APP_NAME}.dmg\""

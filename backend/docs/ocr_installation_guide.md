# Tesseract OCR 安装指南

## 📋 系统要求
- Windows 10/11, macOS, 或 Linux
- Python 3.7+

## 🚀 安装步骤

### Windows 安装
1. **下载Tesseract OCR安装程序**：
   - 官方下载：https://github.com/UB-Mannheim/tesseract/wiki
   - 选择最新稳定版

2. **运行安装程序**，选择安装路径（建议默认路径）

3. **安装中文语言包（必须）**：
   - 在安装过程中选择语言包（中文简体：chi_sim）
   - 如果安装时未选择，需要手动下载并安装：
     - 下载地址：https://github.com/tesseract-ocr/tessdata_best/tree/main
     - 文件名：`chi_sim.traineddata`
     - 将文件复制到：`C:\Program Files\Tesseract-OCR\tessdata\`

4. **将Tesseract添加到系统PATH**：
   - 右键"此电脑" → "属性" → "高级系统设置"
   - 点击"环境变量"
   - 在"系统变量"中找到"Path"，点击"编辑"
   - 添加Tesseract安装路径（如：C:\Program Files\Tesseract-OCR）

5. **验证安装**：
   ```bash
   tesseract --version
   tesseract --list-langs  # 确认chi_sim在列表中
   ```

### macOS 安装（使用Homebrew）
```bash
brew install tesseract
brew install tesseract-lang  # 安装语言包（包括中文）
```

### Linux 安装（Ubuntu/Debian）
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-chi-sim  # 中文简体（必须）
```

## 🔧 验证安装
```bash
tesseract --list-langs  # 列出可用语言（确认chi_sim存在）
tesseract --version    # 查看版本
```

## 🧠 关键优化（必须做）

### 1. 图像预处理（核心提升精度🔥）
代码中已实现灰度转换和二值化，这是提升识别精度的关键。

### 2. OCR回退机制
当PDF文本提取不足时，自动使用OCR处理：
```python
if len(text.strip()) < 50:  # 文本过少时启动OCR
    text = extract_text_from_pdf(content)
```

### 3. 中文支持配置
确保在代码中使用中文语言包：
```python
lang="chi_sim"  # 中文简体
```

## ⚠️ 必须注意的坑

❗ **中文语言包是必须的** - 没有它无法识别中文！

❗ **图像预处理是核心** - 直接影响识别精度

❗ **PDF处理限制** - Tesseract只能处理图片，需要先转换为图片

❗ **识别精度不稳定** - 建议结合LLM进行二次整理

## 📊 安装后测试
安装完成后，运行测试文件验证：
```bash
python tests/test_ocr.py
```

如果一切正常，您将看到OCR处理结果。

## ⚠️ 注意事项
- 确保Tesseract路径已添加到系统PATH
- 中文支持需要安装中文语言包
- 如果遇到路径问题，可以在代码中指定Tesseract路径：
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

## 📊 安装后测试
安装完成后，运行测试文件验证：
```bash
python tests/test_ocr.py
```

如果一切正常，您将看到OCR处理结果。
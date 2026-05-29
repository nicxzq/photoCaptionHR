# PhotoSign 需求与设计文档

## 1. 项目概述

批量处理两类图片的 Windows 离线工具，通过本地 OCR 识别图片内容，自动完成打勾标记和文件重命名。

---

## 2. 功能需求

### 2.1 任务一：表格图片批量打勾（task: excel）

**输入**
- 一个文件夹，内含一张或多张表格图片（扫描件/拍照件）
- 每张图片是一个人员名单表格，有固定表头（序号、姓名、其他列），表格上方有文档标题

**处理逻辑**
1. 对每张输入图片，OCR 识别表格结构
2. 提取文档标题（表格上方的大字标题，如"聘任中级专业技术职务人员名单"）
3. 识别所有数据行（跳过表头行），提取每行的：
   - 行的像素 Y 坐标范围（用于定位勾的位置）
   - 第二列的姓名文本
4. 按数据行数 N，生成 N 张输出图片：
   - 每张图片 = 原图副本 + 在对应行左侧行头区域绘制红色勾标记
   - 勾的样式：红色圆形背景 + 白色 ✓ 符号，大小约等于一行高度，垂直居中对齐该行
   - 勾绘制在表格最左侧留白处（序号列左侧的空白边距内）
5. 输出文件名格式：`{姓名}-{文档标题}.jpg`

**示例**
- 输入：一张含 17 行数据的表格图片
- 输出：17 张图片，依次为 `张三-聘任中级专业技术职务人员名单.jpg`、`李四-聘任中级专业技术职务人员名单.jpg`……

---

### 2.2 任务二：证件图片批量重命名（task: cert）

**输入**
- 一个文件夹，内含多张证件类图片（文件名无意义）
- 证件样式相似（如"卫生专业技术资格"证书），有固定的标题区和姓名字段

**处理逻辑**
1. 对每张图片，OCR 识别全图文本
2. 提取证件名称：图片顶部最大/最突出的标题文本（如"卫生专业技术资格"）
3. 提取姓名：找到"姓　名："或"姓名："字段后跟随的文本值
4. 将原图片重命名（或复制到输出目录）为 `{姓名}-{证件名}.jpg`

**示例**
- 输入：`sample_certificate.jpg`（含"张三"、"卫生专业技术资格"）
- 输出：`张三-卫生专业技术资格.jpg`

---

### 2.3 通用需求

| 项目 | 要求 |
|------|------|
| 运行环境 | Windows 10+，Python 3.9+ |
| 联网要求 | 完全离线，不依赖任何在线 API |
| 输入格式 | jpg、jpeg、png（可扩展） |
| 输出格式 | jpg |
| 调用方式 | CLI 命令行（必须）；可选 tkinter 简单 GUI |
| 错误处理 | 单文件失败不影响批处理其他文件，失败信息输出到控制台 |
| 文件名冲突 | 若输出文件已存在，自动追加 `_2`、`_3` 等后缀 |

---

## 3. 技术选型

### 3.1 OCR 引擎：PaddleOCR（离线首选）

```
pip install paddlepaddle paddleocr
```

- **中文识别精度最优**，专为中文文档设计
- 支持文本检测、文本识别、表格结构识别（PP-Structure）
- 首次运行自动下载模型到本地，之后完全离线
- CPU 可运行，无需 GPU

备选轻量方案：`rapidocr-onnxruntime`（体积更小，精度略低）

### 3.2 图像处理：OpenCV + Pillow

- **OpenCV**：检测表格横线，精确定位每行像素边界
- **Pillow**：绘制红色勾标记，保存输出图片

### 3.3 打包：PyInstaller

```
pip install pyinstaller
pyinstaller --onefile main.py
```

生成单个 `.exe`，无需安装 Python 环境即可运行。

---

## 4. 项目结构

```
photosign/
├── main.py                 # CLI 入口
├── requirements.txt
├── core/
│   ├── ocr_engine.py       # PaddleOCR 封装（单例，懒加载）
│   ├── task_excel.py       # 任务一实现
│   └── task_cert.py        # 任务二实现
├── utils/
│   ├── image_draw.py       # 绘制红色勾标记
│   ├── table_detect.py     # 表格行边界检测（OpenCV）
│   └── file_utils.py       # 输出路径生成、文件名去重
├── input/
│   ├── excelFile/          # 示例输入（任务一）
│   └── zhengjian/          # 示例输入（任务二）
└── output/
    ├── excelFile/          # 示例输出（任务一）
    └── zhengjian/          # 示例输出（任务二）
```

---

## 5. 核心模块设计

### 5.1 `core/ocr_engine.py`

```python
# 单例封装，避免重复初始化（PaddleOCR 初始化耗时约 3-5s）
class OCREngine:
    _instance = None

    @classmethod
    def get(cls) -> PaddleOCR:
        if cls._instance is None:
            cls._instance = PaddleOCR(use_angle_cls=True, lang='ch', show_log=False)
        return cls._instance

    @classmethod
    def ocr_image(cls, img_path: str) -> list[dict]:
        # 返回格式: [{"text": str, "bbox": [x1,y1,x2,y2], "score": float}]
        ...
```

### 5.2 `utils/table_detect.py`

**表格行边界检测（任务一核心）**

```
算法：
1. 读取原图 -> 转灰度 -> 二值化（Otsu）
2. 形态学操作：用宽水平核腐蚀+膨胀，提取水平线
3. 用 cv2.HoughLinesP 或 cv2.findContours 找到所有水平线段
4. 过滤短线段（长度 < 图宽 * 0.5），保留跨越大部分表格宽度的线
5. 按 Y 坐标排序，相邻两线 Y 值确定一行的上下边界
6. 返回 rows: list[tuple[int, int]]  # [(y_top, y_bottom), ...]
```

### 5.3 `utils/image_draw.py`

**绘制红色勾标记**

```
函数签名：
draw_checkmark(img: PIL.Image, y_top: int, y_bottom: int, left_margin: int) -> PIL.Image

逻辑：
1. 计算圆心 Y = (y_top + y_bottom) / 2，X = left_margin / 2
2. 半径 r = min((y_bottom - y_top) * 0.4, left_margin * 0.4)
3. 用 ImageDraw 绘制红色实心圆（fill="#E53935"）
4. 在圆内绘制白色 ✓ 折线路径：
   - 起点：圆心偏左下约 (cx - r*0.4, cy + r*0.1)
   - 中间点：(cx - r*0.1, cy + r*0.35)
   - 终点：(cx + r*0.4, cy - r*0.25)
   - 线宽：max(2, r * 0.18)
```

### 5.4 `core/task_excel.py`

```
函数：process_excel_image(input_path, output_dir)

流程：
1. OCR 全图 -> 获取所有文本块（含 bbox）
2. 提取文档标题：
   - 过滤 Y 坐标小于图高 * 0.25 的文本块
   - 取字符数 > 8 且不含"序号""姓名"等表头词的最长文本
3. 检测表格横线 -> 得到行边界列表 rows
4. 匹配每行的姓名：
   - 找到表头行（含"姓名"文本的行）的行索引 header_row_idx
   - 对每个数据行（header_row_idx+1 之后的行）：
     a. 收集 bbox 在该行 Y 范围内的所有文本块
     b. 按 X 坐标排序，取第二个文本块（姓名列）
5. 对每个数据行：
   a. 深拷贝原图
   b. draw_checkmark(img, row_y_top, row_y_bottom, left_margin=行最左 X - 10)
   c. 生成输出路径：resolve_output_path(output_dir, f"{name}-{title}.jpg")
   d. 保存
```

### 5.5 `core/task_cert.py`

```
函数：process_cert_image(input_path, output_dir)

流程：
1. OCR 全图 -> 获取所有文本块（含 bbox）
2. 提取证件名称：
   - 过滤 Y 坐标 < 图高 * 0.3 的文本块
   - 去除英文行（全为 ASCII 的行）
   - 取最长中文文本块的 text（即标题行）
3. 提取姓名：
   - 遍历文本块，找到 text 匹配正则 r"姓\s*名[：:]?" 的块
   - 取该块同行（Y 差 < 行高 * 1.5）且 X 坐标更大的文本块
   - 若未找到，尝试找"姓　名"后紧跟的下一个非空文本块
4. 生成输出路径：resolve_output_path(output_dir, f"{name}-{cert_title}.jpg")
5. 复制（不删除原文件）到输出目录并重命名
```

### 5.6 `utils/file_utils.py`

```python
def resolve_output_path(output_dir: str, filename: str) -> str:
    # 处理文件名中的非法字符（替换为 _）
    # 若文件已存在，追加 _2、_3 后缀
    ...
```

### 5.7 `main.py`（CLI 入口）

```
用法：
  python main.py --task excel --input ./input/excelFile --output ./output/excelFile
  python main.py --task cert  --input ./input/zhengjian  --output ./output/zhengjian

参数：
  --task    必填，excel 或 cert
  --input   必填，输入文件夹路径
  --output  必填，输出文件夹路径（不存在则自动创建）
  --ext     可选，处理的图片扩展名，默认 jpg,jpeg,png

输出：
  逐文件打印处理结果，最终汇总成功/失败数
```

---

## 6. 关键技术细节

### 6.1 表格左侧留白宽度估算

表格最左列（序号列）的 bbox x1 即为表格左边界。图片左边距 = x1（表格序号列左边 X）。
勾标记绘制在 x=0 到 x=x1 之间的区域内水平居中。

若 x1 < 40px（边距太窄），则将原图用 Pillow 在左侧扩展 60px 白色画布，再绘制。

### 6.2 OCR 结果后处理

PaddleOCR 返回格式：
```python
result = ocr.ocr(img_path, cls=True)
# result[0] = [[[x1,y1],[x2,y1],[x2,y2],[x1,y2]], (text, score)]
```
统一转换为：
```python
{"text": str, "bbox": (x1, y1, x2, y2), "score": float}
```
其中 bbox 取四点坐标的外接矩形。

### 6.3 多页表格（表格跨图）

当前版本：每张图片独立处理，不合并跨图表格。
文件名若有重复（同一表格标题），自动追加序号后缀。

### 6.4 离线模型下载

首次运行时 PaddleOCR 自动下载模型到 `~/.paddleocr/`（约 100-200MB）。
之后断网可正常运行。
可在 README 中提示用户首次需联网。

---

## 7. requirements.txt

```
paddlepaddle>=2.6.0
paddleocr>=2.7.0
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
```

---

## 8. 打包为 Windows 可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --name photosign main.py
# 生成 dist/photosign.exe
```

注意：PaddlePaddle 体积较大（~500MB），打包后 exe 较大。
可改用 `rapidocr-onnxruntime` + `onnxruntime`（总体积约 80MB）作为轻量替代。

---

## 9. 边界情况处理

| 情况 | 处理方式 |
|------|---------|
| OCR 未检测到姓名 | 跳过该行，打印警告 |
| OCR 未检测到文档标题 | 使用输入文件名（去扩展名）作为标题 |
| 表格横线检测失败 | 降级方案：用 OCR 文本块的 Y 坐标聚类估算行边界 |
| 输出文件名含非法字符（/ \ : * ? " < > \|） | 替换为下划线 |
| 图片旋转/倾斜 | PaddleOCR 的 `use_angle_cls=True` 自动矫正 |
| 同名输出文件 | 追加 `_2`、`_3` 后缀 |

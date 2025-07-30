# Windows系统Python安装&使用指南

## 第一步：下载Python

1. 打开浏览器，访问Python官网：https://www.python.org/
2. 点击页面上的 **"Downloads"** 按钮
3. 网站会自动识别你的Windows系统，显示 **"Download Python 3.x.x"** 按钮
4. 点击这个黄色的下载按钮，开始下载Python安装包

## 第二步：安装Python

1. 找到刚才下载的文件（通常在"下载"文件夹中），双击运行
2. **重要**：在安装界面的最下方，勾选 **"Add Python to PATH"** 选项
   - 这一步很重要，勾选后可以自动配置环境变量
3. 点击 **"Install Now"** 开始安装
4. 等待安装完成，看到 **"Setup was successful"** 提示即可

## 第三步：验证安装是否成功

1. 按 **Win + R** 键，打开"运行"对话框
2. 输入 **cmd** 并按回车，打开命令提示符
3. 在黑色窗口中输入：`python --version`
4. 如果显示Python版本号（如：Python 3.11.0），说明安装成功

## 第四步：手动配置环境变量（如果第二步没有勾选）

如果在安装时忘记勾选"Add Python to PATH"，可以手动配置：

1. 右键点击 **"此电脑"** → 选择 **"属性"**
2. 点击 **"高级系统设置"**
3. 点击 **"环境变量"** 按钮
4. 在"系统变量"区域找到 **"Path"**，双击打开
5. 点击 **"新建"**，添加Python安装路径：
   - 通常是：`C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\`
   - 再添加：`C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\Scripts\`
6. 点击 **"确定"** 保存所有设置
7. 重新打开命令提示符测试

## 第五步：安装常用工具

在命令提示符中输入以下命令，安装pip包管理工具（通常已自动安装）：
```
python -m pip install --upgrade pip
```

## 常见问题解决

### 问题1：输入python命令提示"不是内部或外部命令"
**解决方法**：说明环境变量没有配置好，请按照第四步重新配置

### 问题2：安装时提示权限不足
**解决方法**：右键点击安装包，选择"以管理员身份运行"

### 问题3：找不到Python安装路径
**解决方法**：
1. 在开始菜单搜索"Python"
2. 右键点击Python程序 → "打开文件位置"
3. 复制这个路径用于环境变量配置

### 问题4：python命令可以使用，但pip命令提示"不是内部或外部命令"
**解决方法**：这说明环境变量中缺少pip的路径，需要添加Scripts文件夹：
1. 按照第四步的方法打开环境变量设置
2. 在Path中添加Python的Scripts目录：
   - 通常是：`C:\Users\你的用户名\AppData\Local\Programs\Python\Python311\Scripts\`
   - 注意：这个路径末尾有\Scripts\
3. 保存设置后重新打开命令提示符
4. 输入 `pip --version` 测试是否成功

**如果还是不行，可以尝试**：
- 使用完整路径：`python -m pip --version`
- 重新安装Python时勾选"Add Python to PATH"选项

### 万能解决方案：重启电脑
如果以上所有方法都尝试过了，问题仍然存在，请尝试**重启电脑**：
- 环境变量的修改有时需要重启才能完全生效
- 重启后重新打开命令提示符测试
- 这个方法可以解决大部分环境配置相关的问题

**重启后仍有问题**：
- 考虑完全卸载Python后重新安装
- 安装时务必勾选"Add Python to PATH"选项

## 第六步：运行Python项目

安装好Python后，你可能需要运行别人写好的Python项目。以下是完整步骤：

### 1. 获取项目文件
- 从GitHub、邮件或其他渠道下载项目文件
- 解压到一个容易找到的位置（如桌面或D盘）

### 2. 打开项目文件夹
1. 按 **Win + R** 键，输入 **cmd** 打开命令提示符
2. 使用 **cd** 命令进入项目文件夹，例如：
   ```
   cd D:\my_python_project
   ```
   （将路径替换为你的实际项目路径）

### 3. 安装项目依赖
大多数Python项目都有一个 **requirements.txt** 文件，里面列出了需要的软件包。

在项目文件夹中输入以下命令：
```
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

**说明**：
- `pip install -r requirements.txt`：安装项目所需的所有依赖包
- `-i https://pypi.tuna.tsinghua.edu.cn/simple/`：使用清华大学镜像源，下载速度更快

### 4. 运行Python脚本
安装完依赖后，就可以运行项目了：
```
python main.py
```
（将 `main.py` 替换为项目的主要脚本文件名）

### 5. 常见运行问题

**问题1：找不到requirements.txt文件**
- 检查是否在正确的项目文件夹中
- 有些项目可能没有这个文件，直接运行脚本即可

**问题2：安装依赖时出现错误**
- 尝试升级pip：`python -m pip install --upgrade pip`
- 如果还有问题，可以逐个安装：`pip install 包名`

**问题3：运行脚本时提示缺少模块**
- 说明有依赖包没有安装成功
- 根据错误提示安装对应的包：`pip install 模块名`

### 6. 实用技巧

**查看已安装的包**：
```
pip list
```

**查看项目文件**：
```
dir
```
（在命令提示符中查看当前文件夹内容）

**退出程序**：
- 如果程序一直在运行，按 **Ctrl + C** 可以停止

## 完成！

现在你已经掌握了Python的安装和基本使用方法！可以开始运行各种Python项目了。

**小贴士**：
- 建议安装一个代码编辑器，如VS Code或PyCharm，让编程更加方便
- 遇到问题时，可以复制错误信息到搜索引擎查找解决方案
- 多练习几次，很快就能熟练掌握这些操作
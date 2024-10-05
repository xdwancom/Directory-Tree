import os
import time
import ctypes
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog

# 指定要跳过的文件夹
skip_directories = [r'']


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_ulong),
                ("dwHighDateTime", ctypes.c_ulong)]


def convert_to_filetime(timestamp):
    """转换时间戳为 Windows FILETIME 格式"""
    return FILETIME(
        dwLowDateTime=int((timestamp + 11644473600) * 10000000) & 0xFFFFFFFF,
        dwHighDateTime=int((timestamp + 11644473600) * 10000000) >> 32
    )


def set_file_times(target_path, create_time, mod_time):
    """设置文件的创建和修改时间"""
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateFileW(target_path, 0x40000000, 0, None, 3, 0, None)

        if handle == -1:
            print(f"Failed to create file handle for {target_path}.")
            return

        create_time_ft = convert_to_filetime(create_time)
        mod_time_ft = convert_to_filetime(mod_time)

        kernel32.SetFileTime(handle, ctypes.byref(create_time_ft), None, ctypes.byref(mod_time_ft))
        kernel32.CloseHandle(handle)


def create_empty_file_with_timestamps(source_path, target_path):
    """创建空文件并设置时间戳"""
    try:
        # 创建空文件
        open(target_path, 'w').close()

        # 获取源文件的修改时间和创建时间
        mod_time = os.path.getmtime(source_path)
        create_time = os.path.getctime(source_path)

        # 设置文件时间
        os.utime(target_path, (mod_time, mod_time))
        set_file_times(target_path, create_time, mod_time)
        return 1  # 返回已处理的文件数量
    except Exception as e:
        print(f"Error processing {source_path}: {e}")
        return 0  # 如果有错误返回0


def create_empty_files_with_timestamps(source_directory, target_directory, skip_dirs):
    """遍历源目录并创建空文件，设置时间戳，跳过指定的文件夹"""
    os.makedirs(target_directory, exist_ok=True)

    total_processed = 0  # 初始化已处理文件计数
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:  # 指定线程数为CPU线程数
        futures = []
        for item in os.listdir(source_directory):
            source_path = os.path.join(source_directory, item)
            target_path = os.path.join(target_directory, item)

            # 跳过指定的文件夹
            if any(os.path.abspath(source_path).startswith(os.path.abspath(skip_dir)) for skip_dir in skip_dirs):
                print(f'跳过指定文件夹: {source_path}')
                continue

            if os.stat(source_path).st_file_attributes & 0x02:  # 检查是否为隐藏文件
                print(f'跳过隐藏文件: {source_path}')
                continue

            if os.path.isdir(source_path):
                # 对于目录递归调用
                processed_count = create_empty_files_with_timestamps(source_path, target_path, skip_dirs)
                total_processed += processed_count
                print(f'创建:  {target_path}')
            else:
                future = executor.submit(create_empty_file_with_timestamps, source_path, target_path)
                futures.append(future)

        # 等待所有任务完成并统计已处理的文件
        for future in futures:
            total_processed += future.result()

    return total_processed  # 返回总处理文件数量


def run_process():
    source_directory = source_entry.get()
    target_directory = target_entry.get()
    skip_dirs = skip_text.get("1.0", tk.END).strip().splitlines()  # 获取多行输入并转为列表

    if not os.path.isdir(source_directory):
        messagebox.showerror("错误", "源目录无效")
        return
    if not os.path.isdir(target_directory):
        messagebox.showerror("错误", "目标目录无效")
        return

    # 开始计时
    start_time = time.perf_counter()  # 使用高精度计时
    # 调用函数
    processed_count = create_empty_files_with_timestamps(source_directory, target_directory, skip_dirs)
    # 结束计时
    elapsed_time = (time.perf_counter() - start_time) * 1000

    messagebox.showinfo("完成", f"文件处理完成!\n已处理文件数量: {processed_count}\n运行时间: {elapsed_time:.2f} 毫秒")


def browse_source():
    directory = filedialog.askdirectory()
    source_entry.delete(0, tk.END)
    source_entry.insert(0, directory)


def browse_target():
    directory = filedialog.askdirectory()
    target_entry.delete(0, tk.END)
    target_entry.insert(0, directory)


# 创建主窗口
root = tk.Tk()
root.title("文件目录树备份工具")

# 创建源目录输入框
tk.Label(root, text="源目录:").grid(row=0, column=0, padx=10, pady=10)
source_entry = tk.Entry(root, width=50)
source_entry.grid(row=0, column=1, padx=10, pady=10)
tk.Button(root, text="浏览", command=browse_source).grid(row=0, column=2, padx=10, pady=10)

# 创建目标目录输入框
tk.Label(root, text="目标目录:").grid(row=1, column=0, padx=10, pady=10)
target_entry = tk.Entry(root, width=50)
target_entry.grid(row=1, column=1, padx=10, pady=10)
tk.Button(root, text="浏览", command=browse_target).grid(row=1, column=2, padx=10, pady=10)

# 跳过的文件夹输入框
tk.Label(root, text="跳过的文件夹 (选填，可添加多条路径，1行1条):").grid(row=2, column=0)
skip_text = scrolledtext.ScrolledText(root, width=40, height=10)
skip_text.grid(row=2, column=1)

# 开始按钮
start_button = tk.Button(root, text="开始运行", command=run_process)
start_button.grid(row=3, columnspan=2)

# 启动主循环
root.mainloop()
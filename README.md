# Automatic File Organizer

A Python-based desktop application that automatically organizes files into category-based folders according to their file extensions.

The application provides both a GUI interface and a command-line interface, supports real-time folder monitoring, duplicate-file protection, Dry Run mode, statistics, system tray operation, and an external configuration file.

---

## Features

- Automatically organizes files by extension
- Real-time file monitoring
- Processes existing files when the organizer starts
- Supports multiple file categories
- Unknown file types are moved to `Others`
- Files without extensions are moved to `Others`
- Prevents duplicate files from being overwritten
- Ignores temporary and unwanted files
- Dry Run mode for testing
- Start/Stop organizer controls
- Activity log
- File organization statistics
- System tray support
- External `config.json` configuration
- Error handling and logging
- Standalone Windows `.exe` version

---

## File Categories

The default categories are:

| Category | Examples |
| --- | --- |
| Images | `.jpg`, `.png`, `.gif`, `.webp`, `.svg` |
| Documents | `.pdf`, `.docx`, `.txt`, `.xlsx`, `.csv` |
| Audio | `.mp3`, `.wav`, `.flac`, `.aac` |
| Videos | `.mp4`, `.mkv`, `.avi`, `.mov` |
| Software | `.exe`, `.msi`, `.bat`, `.cmd`, `.py` |
| Archives | `.zip`, `.rar`, `.7z`, `.tar`, `.gz` |
| Others | Unknown extensions and files without extensions |

---

## Project Structure

```text
Automatic_File_Organizer/
│
├── main.py
├── config.json
├── organizer.log
├── README.md
│
├── test_folder/
│   ├── Images/
│   ├── Documents/
│   ├── Audio/
│   ├── Videos/
│   ├── Software/
│   ├── Archives/
│   └── Others/
│
└── dist/
    ├── Automatic_File_Organizer.exe
    └── config.json

```

---

## Requirements

For running the Python source code:

* Python 3.x
* watchdog
* pystray
* Pillow
* tkinter

Install the required Python packages with:

```bash
python -m pip install watchdog pystray pillow

```

---

## Running the Python Version

Open PowerShell and navigate to the project folder:

```powershell
cd "D:\Projects\Automatic_File_Organizer"

```

Run the application:

```bash
python main.py

```

The graphical interface will open.

---

## Command-Line Options

### Normal Mode

```bash
python main.py

```

### Dry Run Mode

```bash
python main.py --dry-run

```

Dry Run mode detects files and shows what would happen without actually moving the files.

### Help

```bash
python main.py --help

```

---

## Using the Windows EXE

A standalone Windows executable is available in:

```text
dist\Automatic_File_Organizer.exe

```

The executable requires the configuration file:

```text
dist\config.json

```

Keep both files together.

Double-click `Automatic_File_Organizer.exe` to start the application.

---

## How It Works

When the organizer starts, it first checks the monitored folder for existing files.

It then continuously monitors the folder for new files.

For each file:

1. The file extension is detected.
2. The extension is compared with `config.json`.
3. The appropriate category is selected.
4. The destination folder is created if necessary.
5. The file is moved to the category folder.
6. If a file with the same name already exists, a new name is generated.
7. The action is recorded in the activity log and statistics.

Example: `photo.jpg` is automatically moved to `Images/photo.jpg`.

---

## Duplicate File Protection

The organizer does not overwrite existing files.

For example, if `photo.jpg` already exists, another file with the same name may become `photo_1.jpg`.

If another duplicate is added, it becomes `photo_2.jpg`.

This prevents accidental data loss.

---

## Ignored Files

Some files are intentionally ignored.

Examples include:

* `.tmp`
* `.temp`
* `.part`
* `.crdownload`
* `.lnk`

Files beginning with `~` are also ignored.

The organizer also ignores its own `organizer.log` and `config.json` when they appear inside the monitored folder.

---

## Configuration

File categories and extensions are controlled through `config.json`.

Example:

```json
{
    "Images": [
        ".jpg",
        ".jpeg",
        ".png"
    ],
    "Documents": [
        ".pdf",
        ".docx",
        ".txt"
    ]
}

```

This allows file types to be added or removed without modifying the Python source code.

### Adding a New File Extension

Open `config.json`.

Suppose you want `.json` files to be treated as documents. Add `".json"` inside the `Documents` list.

After saving the configuration, restart the organizer.

---

## Dry Run Mode

Dry Run mode allows the user to test the organizer without actually moving files.

Example activity log:

```text
[DRY RUN] Screenshot.png -> Images/Screenshot.png

```

The file remains in its original location. This is useful when testing a new configuration.

---

## Statistics

The application tracks:

* Processed files
* Moved files
* Ignored files
* Unknown files
* Errors
* Dry Run operations

The GUI displays these statistics while the organizer is running.

---

## System Tray

The application can run in the background through the Windows system tray.

The GUI provides:

* Start Organizer
* Stop Organizer
* Minimize to Tray

This allows the organizer to continue monitoring the folder without keeping the main window visible.

---

## Logging

Application activity is recorded in `organizer.log`.

The log contains information about:

* Files detected
* Files moved
* Ignored files
* Dry Run operations
* Errors
* Organizer sessions

---

## Error Handling

The application handles common file-system issues such as:

* Permission errors
* Files being removed before processing
* File-system errors
* Unexpected processing errors

Errors are recorded rather than causing the entire application to terminate.

---

## Technologies Used

* Python
* Tkinter
* Watchdog
* Pystray
* Pillow
* JSON
* PyInstaller

---

## Project Purpose

This project was created to practice and demonstrate:

* Python file handling
* Automation
* File-system monitoring
* GUI development
* Configuration management
* Logging
* Exception handling
* Multithreading
* Desktop application development
* Windows executable packaging

---

## Future Improvements

Possible future versions may include:

* Custom folder selection
* Multiple monitored folders
* Custom categories from the GUI
* Scheduled organization
* Advanced filtering
* File preview
* Improved tray controls
* Automatic startup with Windows
* More detailed statistics
* User-configurable ignored extensions

---

## Version & Details

**Version:** 1.0

**Status:** Stable

**Author:** Cherman Eswar T

**Degree:** B.Tech Information Technology
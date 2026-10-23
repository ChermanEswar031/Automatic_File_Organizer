from pathlib import Path
import shutil
import time
import argparse
import json
import threading
import queue
import sys
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import pystray
from PIL import Image, ImageDraw


# ============================================================
# PROJECT PATHS
# ============================================================

# When running normally:
# Uses the project folder.
#
# When running as a PyInstaller .exe:
# Uses the folder where the .exe is located.
#
# This prevents config.json from being searched for inside
# PyInstaller's temporary _MEI folder.

if getattr(sys, "frozen", False):

    project_folder = (
        Path(sys.executable).resolve().parent
    )

else:

    project_folder = (
        Path(__file__).resolve().parent
    )


folder = project_folder / "test_folder"
log_file = project_folder / "organizer.log"
config_file = project_folder / "config.json"


# ============================================================
# COMMAND-LINE ARGUMENTS
# ============================================================

parser = argparse.ArgumentParser(
    description="Automatic File Organizer"
)

parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Preview file movements without actually moving files"
)

args = parser.parse_args()


# ============================================================
# CONFIGURATION
# ============================================================

def load_configuration():

    try:

        with open(
            config_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except FileNotFoundError:

        raise FileNotFoundError(
            f"Configuration file not found:\n{config_file}"
        )

    except json.JSONDecodeError:

        raise ValueError(
            f"Invalid JSON in configuration file:\n{config_file}"
        )


file_categories = load_configuration()

categories = set(file_categories.keys())
categories.add("Others")


# ============================================================
# IGNORED FILES
# ============================================================

ignored_extensions = {
    ".tmp",
    ".temp",
    ".part",
    ".crdownload",
    ".lnk"
}


ignored_files = {
    log_file.name,
    config_file.name
}


# ============================================================
# SESSION VARIABLES
# ============================================================

session_start = None
session_id = None

DRY_RUN = args.dry_run

observer = None
organizer_thread = None

stop_event = threading.Event()

running = False

tray_icon = None


# ============================================================
# STATISTICS
# ============================================================

stats = {
    "processed": 0,
    "moved": 0,
    "dry_run": 0,
    "ignored": 0,
    "unknown": 0,
    "errors": 0
}


category_stats = {}


# ============================================================
# GUI QUEUE
# ============================================================

ui_queue = queue.Queue()


def notify(message):

    print(message)

    ui_queue.put(
        ("message", message)
    )


def update_gui_statistics():

    ui_queue.put(
        (
            "stats",
            stats.copy(),
            category_stats.copy()
        )
    )


# ============================================================
# LOGGING
# ============================================================

def log_action(action, file_path, extra=""):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    message = (
        f"[{timestamp}] "
        f"[Session: {session_id}] "
        f"[{action}] "
        f"{file_path}"
    )

    if extra:

        message += f" | {extra}"

    with open(
        log_file,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            message + "\n"
        )


# ============================================================
# CATEGORY FOLDERS
# ============================================================

def create_category_folders():

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    for category in categories:

        (folder / category).mkdir(
            exist_ok=True
        )


# ============================================================
# UNIQUE DESTINATION
# ============================================================

def get_unique_destination(destination):

    if not destination.exists():

        return destination

    counter = 1

    while True:

        new_name = (
            f"{destination.stem}_"
            f"{counter}"
            f"{destination.suffix}"
        )

        new_destination = (
            destination.parent / new_name
        )

        if not new_destination.exists():

            return new_destination

        counter += 1


# ============================================================
# FILE READY CHECK
# ============================================================

def wait_until_file_is_ready(
    file_path,
    checks=5,
    delay=0.2
):

    previous_size = -1

    for _ in range(checks):

        if not file_path.exists():

            return False

        try:

            current_size = (
                file_path.stat().st_size
            )

        except OSError:

            return False

        if current_size == previous_size:

            return True

        previous_size = current_size

        time.sleep(delay)

    return True


# ============================================================
# ORGANIZE FILE
# ============================================================

def organize_file(file_path):

    if not file_path.is_file():

        return

    stats["processed"] += 1

    update_gui_statistics()


    # --------------------------------------------------------
    # Protected files
    # --------------------------------------------------------

    if file_path.name in ignored_files:

        stats["ignored"] += 1

        notify(
            f"[IGNORED] Protected file: "
            f"{file_path.name}"
        )

        log_action(
            "IGNORED",
            file_path,
            "Protected file"
        )

        update_gui_statistics()

        return


    # --------------------------------------------------------
    # Temporary extensions
    # --------------------------------------------------------

    if file_path.suffix.lower() in ignored_extensions:

        stats["ignored"] += 1

        notify(
            f"[IGNORED] Temporary file: "
            f"{file_path.name}"
        )

        log_action(
            "IGNORED",
            file_path,
            "Temporary file"
        )

        update_gui_statistics()

        return


    # --------------------------------------------------------
    # Temporary filenames
    # --------------------------------------------------------

    if file_path.name.startswith("~"):

        stats["ignored"] += 1

        notify(
            f"[IGNORED] Temporary name: "
            f"{file_path.name}"
        )

        log_action(
            "IGNORED",
            file_path,
            "Temporary filename"
        )

        update_gui_statistics()

        return


    # --------------------------------------------------------
    # Wait for file to become ready
    # --------------------------------------------------------

    if not wait_until_file_is_ready(file_path):

        stats["errors"] += 1

        notify(
            f"[ERROR] File was not ready: "
            f"{file_path.name}"
        )

        log_action(
            "ERROR",
            file_path,
            "File was not ready"
        )

        update_gui_statistics()

        return


    # --------------------------------------------------------
    # Determine category
    # --------------------------------------------------------

    extension = file_path.suffix.lower()

    category = "Others"

    if extension:

        found_category = False

        for category_name, extensions in file_categories.items():

            if extension in extensions:

                category = category_name
                found_category = True

                break

        if not found_category:

            stats["unknown"] += 1

            notify(
                f"[UNKNOWN] "
                f"{file_path.name} -> Others"
            )

            log_action(
                "UNKNOWN",
                file_path,
                "Unknown extension"
            )

    else:

        stats["unknown"] += 1

        notify(
            f"[UNKNOWN] "
            f"No extension: {file_path.name}"
        )

        log_action(
            "UNKNOWN",
            file_path,
            "No extension detected"
        )


    # --------------------------------------------------------
    # Destination
    # --------------------------------------------------------

    destination_folder = (
        folder / category
    )

    destination_folder.mkdir(
        exist_ok=True
    )

    destination = (
        destination_folder /
        file_path.name
    )

    destination = get_unique_destination(
        destination
    )


    # --------------------------------------------------------
    # Dry-run
    # --------------------------------------------------------

    if DRY_RUN:

        stats["dry_run"] += 1

        category_stats[category] = (
            category_stats.get(category, 0) + 1
        )

        notify(
            f"[DRY RUN] "
            f"{file_path.name} -> "
            f"{category}/{destination.name}"
        )

        log_action(
            "DRY_RUN",
            file_path,
            f"Would move to {destination}"
        )

        update_gui_statistics()

        return


    # --------------------------------------------------------
    # Move file
    # --------------------------------------------------------

    try:

        shutil.move(
            str(file_path),
            str(destination)
        )

        stats["moved"] += 1

        category_stats[category] = (
            category_stats.get(category, 0) + 1
        )

        notify(
            f"[MOVED] "
            f"{file_path.name} -> "
            f"{category}/{destination.name}"
        )

        log_action(
            "MOVED",
            file_path,
            f"Destination: {destination}"
        )

        update_gui_statistics()


    except PermissionError:

        stats["errors"] += 1

        notify(
            f"[ERROR] Permission denied: "
            f"{file_path.name}"
        )

        log_action(
            "ERROR",
            file_path,
            "Permission denied"
        )

        update_gui_statistics()


    except FileNotFoundError:

        stats["errors"] += 1

        notify(
            f"[ERROR] File disappeared: "
            f"{file_path.name}"
        )

        log_action(
            "ERROR",
            file_path,
            "File not found"
        )

        update_gui_statistics()


    except OSError as error:

        stats["errors"] += 1

        notify(
            f"[ERROR] OS error: "
            f"{file_path.name} | {error}"
        )

        log_action(
            "ERROR",
            file_path,
            str(error)
        )

        update_gui_statistics()


    except Exception as error:

        stats["errors"] += 1

        notify(
            f"[ERROR] "
            f"{file_path.name} | {error}"
        )

        log_action(
            "ERROR",
            file_path,
            str(error)
        )

        update_gui_statistics()


# ============================================================
# ORGANIZE EXISTING FILES
# ============================================================

def organize_existing_files():

    notify("")
    notify("Checking existing files...")

    files = [
        item
        for item in folder.iterdir()
        if item.is_file()
    ]

    if not files:

        notify(
            "No existing files found."
        )

        return

    for file_path in files:

        if stop_event.is_set():

            return

        organize_file(file_path)


# ============================================================
# SAVE STATISTICS
# ============================================================

def save_statistics_to_log():

    global session_start

    if session_start is None:

        return

    session_end = datetime.now()

    duration = (
        session_end - session_start
    )

    notify("")
    notify(
        "========== SESSION SUMMARY =========="
    )

    notify(
        f"Files processed : "
        f"{stats['processed']}"
    )

    notify(
        f"Files moved     : "
        f"{stats['moved']}"
    )

    notify(
        f"Dry-run files   : "
        f"{stats['dry_run']}"
    )

    notify(
        f"Ignored files   : "
        f"{stats['ignored']}"
    )

    notify(
        f"Unknown files   : "
        f"{stats['unknown']}"
    )

    notify(
        f"Errors          : "
        f"{stats['errors']}"
    )

    notify(
        f"Duration        : "
        f"{duration}"
    )

    notify("")
    notify("Category statistics:")

    for category, count in category_stats.items():

        notify(
            f"  {category}: {count}"
        )

    notify(
        "====================================="
    )


    try:

        with open(
            log_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write("\n")

            file.write(
                "========== SESSION SUMMARY ==========\n"
            )

            file.write(
                f"Session ID: {session_id}\n"
            )

            file.write(
                f"Session Start: {session_start}\n"
            )

            file.write(
                f"Session End: {session_end}\n"
            )

            file.write(
                f"Duration: {duration}\n"
            )

            file.write(
                f"Files processed: "
                f"{stats['processed']}\n"
            )

            file.write(
                f"Files moved: "
                f"{stats['moved']}\n"
            )

            file.write(
                f"Dry-run files: "
                f"{stats['dry_run']}\n"
            )

            file.write(
                f"Ignored files: "
                f"{stats['ignored']}\n"
            )

            file.write(
                f"Unknown files: "
                f"{stats['unknown']}\n"
            )

            file.write(
                f"Errors: "
                f"{stats['errors']}\n"
            )

            file.write(
                "Category statistics:\n"
            )

            for category, count in category_stats.items():

                file.write(
                    f"  {category}: {count}\n"
                )

            file.write(
                "=====================================\n"
            )


    except Exception as error:

        notify(
            f"[ERROR] "
            f"Could not save statistics: "
            f"{error}"
        )


# ============================================================
# WATCHDOG HANDLER
# ============================================================

class FileHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:

            return

        organize_file(
            Path(event.src_path)
        )


# ============================================================
# ORGANIZER WORKER
# ============================================================

def organizer_worker():

    global observer

    try:

        create_category_folders()

        observer = Observer()

        event_handler = FileHandler()

        observer.schedule(
            event_handler,
            str(folder),
            recursive=False
        )

        observer.start()

        notify("")
        notify(
            "Automatic File Organizer started."
        )

        notify(
            f"Monitoring: {folder}"
        )

        if DRY_RUN:

            notify(
                "Mode: DRY RUN"
            )

        else:

            notify(
                "Mode: NORMAL"
            )

        notify("")

        log_action(
            "STARTED",
            folder,
            "Organizer started"
        )

        organize_existing_files()

        while not stop_event.is_set():

            stop_event.wait(0.5)


    except Exception as error:

        notify(
            f"[ERROR] Organizer failed: "
            f"{error}"
        )

        log_action(
            "ERROR",
            folder,
            str(error)
        )


    finally:

        if observer is not None:

            try:

                observer.stop()
                observer.join()

            except Exception:

                pass

            observer = None

        save_statistics_to_log()

        ui_queue.put(
            ("stopped", None)
        )


# ============================================================
# CREATE TRAY ICON
# ============================================================

def create_tray_image():

    image = Image.new(
        "RGB",
        (64, 64),
        "white"
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (10, 10, 54, 54),
        outline="black",
        width=4
    )

    draw.line(
        (10, 30, 54, 30),
        fill="black",
        width=4
    )

    draw.line(
        (32, 10, 32, 54),
        fill="black",
        width=4
    )

    return image


# ============================================================
# TRAY FUNCTIONS
# ============================================================

def show_window():

    root.after(
        0,
        root.deiconify
    )

    root.after(
        0,
        root.lift
    )


def hide_window():

    root.after(
        0,
        root.withdraw
    )


def tray_start(icon, item):

    root.after(
        0,
        app.start_organizer
    )


def tray_stop(icon, item):

    root.after(
        0,
        app.stop_organizer
    )


def tray_exit(icon, item):

    root.after(
        0,
        app.close_application
    )


def setup_tray():

    global tray_icon

    image = create_tray_image()

    menu = pystray.Menu(

        pystray.MenuItem(
            "Show Organizer",
            lambda icon, item: show_window()
        ),

        pystray.MenuItem(
            "Start Organizer",
            tray_start
        ),

        pystray.MenuItem(
            "Stop Organizer",
            tray_stop
        ),

        pystray.MenuItem(
            "Exit",
            tray_exit
        )
    )

    tray_icon = pystray.Icon(
        "Automatic File Organizer",
        image,
        "Automatic File Organizer",
        menu
    )

    tray_icon.run()


# ============================================================
# GUI
# ============================================================

class OrganizerGUI:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Automatic File Organizer"
        )

        self.root.geometry(
            "850x650"
        )

        self.root.minsize(
            750,
            550
        )

        self.create_widgets()

        self.root.after(
            200,
            self.process_queue
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )


    # ========================================================
    # WIDGETS
    # ========================================================

    def create_widgets(self):

        main_frame = ttk.Frame(
            self.root,
            padding=15
        )

        main_frame.pack(
            fill="both",
            expand=True
        )


        title = ttk.Label(
            main_frame,
            text="Automatic File Organizer",
            font=("Segoe UI", 18, "bold")
        )

        title.pack(
            anchor="w"
        )


        subtitle = ttk.Label(
            main_frame,
            text=(
                "Automatically organize files "
                "into category folders"
            )
        )

        subtitle.pack(
            anchor="w",
            pady=(0, 15)
        )


        # ----------------------------------------------------
        # FOLDER
        # ----------------------------------------------------

        folder_frame = ttk.LabelFrame(
            main_frame,
            text="Monitoring Folder",
            padding=10
        )

        folder_frame.pack(
            fill="x",
            pady=(0, 10)
        )


        ttk.Label(
            folder_frame,
            text=str(folder)
        ).pack(
            anchor="w"
        )


        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        control_frame = ttk.LabelFrame(
            main_frame,
            text="Controls",
            padding=10
        )

        control_frame.pack(
            fill="x",
            pady=(0, 10)
        )


        self.dry_run_var = tk.BooleanVar(
            value=DRY_RUN
        )


        self.dry_run_check = ttk.Checkbutton(
            control_frame,
            text="Dry-run mode",
            variable=self.dry_run_var
        )

        self.dry_run_check.pack(
            side="left",
            padx=(0, 15)
        )


        self.start_button = ttk.Button(
            control_frame,
            text="Start Organizer",
            command=self.start_organizer
        )

        self.start_button.pack(
            side="left",
            padx=5
        )


        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Organizer",
            command=self.stop_organizer,
            state="disabled"
        )

        self.stop_button.pack(
            side="left",
            padx=5
        )


        self.minimize_button = ttk.Button(
            control_frame,
            text="Minimize to Tray",
            command=self.minimize_to_tray
        )

        self.minimize_button.pack(
            side="left",
            padx=5
        )


        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status_frame = ttk.Frame(
            main_frame
        )

        status_frame.pack(
            fill="x",
            pady=(0, 10)
        )


        ttk.Label(
            status_frame,
            text="Status:"
        ).pack(
            side="left"
        )


        self.status_label = ttk.Label(
            status_frame,
            text="Stopped"
        )

        self.status_label.pack(
            side="left",
            padx=5
        )


        ttk.Label(
            status_frame,
            text="Mode:"
        ).pack(
            side="left",
            padx=(30, 0)
        )


        self.mode_label = ttk.Label(
            status_frame,
            text="Normal"
        )

        self.mode_label.pack(
            side="left",
            padx=5
        )


        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        statistics_frame = ttk.LabelFrame(
            main_frame,
            text="Statistics",
            padding=10
        )

        statistics_frame.pack(
            fill="x",
            pady=(0, 10)
        )


        self.processed_label = ttk.Label(
            statistics_frame,
            text="Processed: 0"
        )

        self.processed_label.grid(
            row=0,
            column=0,
            sticky="w",
            padx=10
        )


        self.moved_label = ttk.Label(
            statistics_frame,
            text="Moved: 0"
        )

        self.moved_label.grid(
            row=0,
            column=1,
            sticky="w",
            padx=10
        )


        self.ignored_label = ttk.Label(
            statistics_frame,
            text="Ignored: 0"
        )

        self.ignored_label.grid(
            row=0,
            column=2,
            sticky="w",
            padx=10
        )


        self.unknown_label = ttk.Label(
            statistics_frame,
            text="Unknown: 0"
        )

        self.unknown_label.grid(
            row=1,
            column=0,
            sticky="w",
            padx=10,
            pady=(5, 0)
        )


        self.errors_label = ttk.Label(
            statistics_frame,
            text="Errors: 0"
        )

        self.errors_label.grid(
            row=1,
            column=1,
            sticky="w",
            padx=10,
            pady=(5, 0)
        )


        self.dry_run_label = ttk.Label(
            statistics_frame,
            text="Dry-run: 0"
        )

        self.dry_run_label.grid(
            row=1,
            column=2,
            sticky="w",
            padx=10,
            pady=(5, 0)
        )


        # ----------------------------------------------------
        # ACTIVITY
        # ----------------------------------------------------

        log_frame = ttk.LabelFrame(
            main_frame,
            text="Activity",
            padding=5
        )

        log_frame.pack(
            fill="both",
            expand=True
        )


        self.activity_box = ScrolledText(
            log_frame,
            wrap="word",
            height=15,
            state="disabled",
            font=("Consolas", 10)
        )

        self.activity_box.pack(
            fill="both",
            expand=True
        )


    # ========================================================
    # ACTIVITY MESSAGE
    # ========================================================

    def add_message(self, message):

        self.activity_box.configure(
            state="normal"
        )

        self.activity_box.insert(
            "end",
            message + "\n"
        )

        self.activity_box.see(
            "end"
        )

        self.activity_box.configure(
            state="disabled"
        )


    # ========================================================
    # START
    # ========================================================

    def start_organizer(self):

        global DRY_RUN
        global running
        global organizer_thread
        global session_start
        global session_id
        global stats
        global category_stats

        if running:

            return

        DRY_RUN = self.dry_run_var.get()

        running = True

        stop_event.clear()

        stats = {
            "processed": 0,
            "moved": 0,
            "dry_run": 0,
            "ignored": 0,
            "unknown": 0,
            "errors": 0
        }

        category_stats = {}

        session_start = datetime.now()

        session_id = session_start.strftime(
            "%Y%m%d_%H%M%S"
        )


        self.status_label.config(
            text="Running"
        )


        if DRY_RUN:

            self.mode_label.config(
                text="Dry Run"
            )

        else:

            self.mode_label.config(
                text="Normal"
            )


        self.start_button.config(
            state="disabled"
        )

        self.stop_button.config(
            state="normal"
        )

        self.dry_run_check.config(
            state="disabled"
        )


        self.add_message("")

        self.add_message(
            "Starting organizer..."
        )


        organizer_thread = threading.Thread(
            target=organizer_worker,
            daemon=True
        )

        organizer_thread.start()


    # ========================================================
    # STOP
    # ========================================================

    def stop_organizer(self):

        global running

        if not running:

            return

        self.add_message("")

        self.add_message(
            "Stopping organizer..."
        )

        running = False

        stop_event.set()

        if observer is not None:

            try:

                observer.stop()

            except Exception:

                pass


    # ========================================================
    # MINIMIZE TO TRAY
    # ========================================================

    def minimize_to_tray(self):

        self.root.withdraw()

        self.add_message(
            "Application minimized to system tray."
        )


    # ========================================================
    # QUEUE
    # ========================================================

    def process_queue(self):

        try:

            while True:

                item = ui_queue.get_nowait()

                message_type = item[0]


                if message_type == "message":

                    self.add_message(
                        item[1]
                    )


                elif message_type == "stats":

                    self.update_statistics(
                        item[1]
                    )


                elif message_type == "stopped":

                    self.organizer_stopped()


        except queue.Empty:

            pass


        self.root.after(
            200,
            self.process_queue
        )


    # ========================================================
    # STATISTICS
    # ========================================================

    def update_statistics(
        self,
        current_stats
    ):

        self.processed_label.config(
            text=(
                f"Processed: "
                f"{current_stats['processed']}"
            )
        )

        self.moved_label.config(
            text=(
                f"Moved: "
                f"{current_stats['moved']}"
            )
        )

        self.ignored_label.config(
            text=(
                f"Ignored: "
                f"{current_stats['ignored']}"
            )
        )

        self.unknown_label.config(
            text=(
                f"Unknown: "
                f"{current_stats['unknown']}"
            )
        )

        self.errors_label.config(
            text=(
                f"Errors: "
                f"{current_stats['errors']}"
            )
        )

        self.dry_run_label.config(
            text=(
                f"Dry-run: "
                f"{current_stats['dry_run']}"
            )
        )


    # ========================================================
    # STOPPED
    # ========================================================

    def organizer_stopped(self):

        global running

        running = False

        self.status_label.config(
            text="Stopped"
        )

        self.start_button.config(
            state="normal"
        )

        self.stop_button.config(
            state="disabled"
        )

        self.dry_run_check.config(
            state="normal"
        )

        self.add_message("")

        self.add_message(
            "Organizer stopped."
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def close_application(self):

        global running

        if running:

            answer = messagebox.askyesno(
                "Exit",
                "The organizer is currently running.\n\n"
                "Do you want to stop it and exit?"
            )

            if not answer:

                return

            running = False

            stop_event.set()

            if observer is not None:

                try:

                    observer.stop()

                except Exception:

                    pass

            self.root.after(
                300,
                self.finish_close
            )

        else:

            self.finish_close()


    def finish_close(self):

        global tray_icon

        if running:

            self.root.after(
                300,
                self.finish_close
            )

            return


        if tray_icon is not None:

            try:

                tray_icon.stop()

            except Exception:

                pass

        self.root.destroy()


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = OrganizerGUI(root)

    tray_thread = threading.Thread(
        target=setup_tray,
        daemon=True
    )

    tray_thread.start()

    root.mainloop()
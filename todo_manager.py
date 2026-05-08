import json
import os
import re
from datetime import datetime


class Task:
    """Represents a single to‑do task.

    Attributes
    ----------
    id: int
        Auto‑incremented identifier starting at 1.
    name: str
        Non‑empty name of the task.
    deadline: str
        Date string in ``DD/MM/YYYY`` format. Must be a future date.
    priority: str
        One of ``"Cao"``, ``"Trung bình"`` or ``"Thấp"``.
    status: bool
        ``True`` if completed, ``False`` otherwise.
    """

    def __init__(self, id_: int, name: str, deadline: str, priority: str, status: bool = False):
        self.id = id_
        self.name = name
        self.deadline = deadline
        self.priority = priority
        self.status = status

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "deadline": self.deadline,
            "priority": self.priority,
            "status": self.status,
        }


class TaskManager:
    """Manages a collection of :class:`Task` objects and persists them to JSON."""

    DATA_FILE = "tasks.json"
    PRIORITY_VALUES = ["Cao", "Trung bình", "Thấp"]

    def __init__(self):
        self.tasks: list[Task] = []
        self._load()

    # ---------------------------------------------------------------------
    # Persistence
    # ---------------------------------------------------------------------
    def _load(self):
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    task = Task(
                        id_=item["id"],
                        name=item["name"],
                        deadline=item["deadline"],
                        priority=item["priority"],
                        status=item["status"],
                    )
                    self.tasks.append(task)
            except Exception:
                # Corrupted file – start fresh
                self.tasks = []
        else:
            self.tasks = []

    def _save(self):
        with open(self.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=4)

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _next_id(self) -> int:
        return max((t.id for t in self.tasks), default=0) + 1

    def _find_by_id(self, id_: int):
        for t in self.tasks:
            if t.id == id_:
                return t
        return None

    def _find_by_name(self, name: str):
        name_lower = name.lower()
        for t in self.tasks:
            if t.name.lower() == name_lower:
                return t
        return None

    # ---------------------------------------------------------------------
    # Core functionality
    # ---------------------------------------------------------------------
    def add_task(self, name: str, deadline: str, priority: str):
        """Validate inputs and add a new task.

        The ``deadline`` argument is expected to be a string already validated
        to match ``DD/MM/YYYY`` and to represent today or a future date.
        """
        # Validation
        if not name.strip():
            raise ValueError("Tên công việc không được để trống")
        try:
            deadline_dt = datetime.strptime(deadline, "%d/%m/%Y")
        except ValueError:
            raise ValueError("Định dạng hạn chót phải là DD/MM/YYYY")
        # Deadline must be strictly in the future (greater than today)
        if deadline_dt.date() <= datetime.now().date():
            raise ValueError("Hạn chót phải là ngày trong tương lai (không được là hôm nay)")
        if priority not in self.PRIORITY_VALUES:
            raise ValueError(f"Độ ưu tiên phải là một trong {self.PRIORITY_VALUES}")

        task = Task(
            id_=self._next_id(),
            name=name.strip(),
            deadline=deadline_dt.strftime("%d/%m/%Y"),
            priority=priority,
        )
        self.tasks.append(task)
        self._save()
        return task

    def list_tasks(self):
        # Sort by deadline ascending
        def key(t: Task):
            return datetime.strptime(t.deadline, "%d/%m/%Y")
        return sorted(self.tasks, key=key)

    def mark_complete(self, identifier):
        task = self._resolve_identifier(identifier)
        if task is None:
            raise LookupError("Không tìm thấy công việc")
        task.status = True
        self._save()
        return task

    def delete_task(self, identifier):
        task = self._resolve_identifier(identifier)
        if task is None:
            raise LookupError("Không tìm thấy công việc")
        self.tasks.remove(task)
        self._save()
        return task

    def _resolve_identifier(self, identifier):
        # identifier may be int (STT) or string (name)
        if isinstance(identifier, int):
            # STT is 1‑based index in the *displayed* sorted list
            sorted_tasks = self.list_tasks()
            if 1 <= identifier <= len(sorted_tasks):
                return sorted_tasks[identifier - 1]
            return None
        else:
            return self._find_by_name(str(identifier))

def _print_menu():
    # ASCII menu without emojis to avoid UnicodeEncodeError on Windows consoles
    print("""====================================
[MENU] TO-DO LIST MANAGER
====================================
1. Thêm công việc mới
2. Xem danh sách công việc
3. Đánh dấu hoàn thành
4. Xóa công việc
5. Xuất danh sách ra CSV (mở bằng WPS Sheets)
6. Thoát
====================================""")


def _color_text(text: str, color_code: str) -> str:
    """Wrap *text* with ANSI *color_code* and reset code.

    color_code examples:
        "\033[92m" – green
        "\033[91m" – red
        "\033[93m" – yellow
    """
    reset = "\033[0m"
    return f"{color_code}{text}{reset}"


def _print_tasks(tasks):
    if not tasks:
        print("Danh sách trống.")
        return
    header = "{:<4} | {:<20} | {:<10} | {:<10} | {}".format("STT", "Tên công việc", "Hạn chót", "Ưu tiên", "Trạng thái")
    print("=" * len(header))
    print(header)
    print("=" * len(header))


def _export_to_csv(tasks, filename: str = "tasks.csv"):
    """Export a list of Task objects to a CSV file.

    The CSV columns correspond to the task attributes and are compatible
    with WPS Sheets (or any spreadsheet program). The file is written using
    UTF‑8 encoding to preserve Vietnamese characters.
    """
    import csv

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        # Header
        writer.writerow(["ID", "Tên công việc", "Hạn chót", "Ưu tiên", "Trạng thái"])
        for t in tasks:
            status = "Hoàn thành" if t.status else "Chưa hoàn thành"
            writer.writerow([t.id, t.name, t.deadline, t.priority, status])
    # The following block previously attempted to re‑print the task table after
    # exporting to CSV, but referenced an undefined variable `header`. Since the
    # CSV export does not need to display the table, we simply omit that
    # printing logic.


def main():
    manager = TaskManager()
    while True:
        _print_menu()
        choice = input("Chọn một mục (1-6): ")
        if not choice.isdigit():
            print("[LOI] Lựa chọn không hợp lệ")
            continue
        choice_num = int(choice)
        if choice_num == 1:
            # Gather task details
            while True:
                name = input("Nhập tên công việc: ")
                if not name.strip():
                    print("[LOI] LỖI: Tên công việc không được để trống")
                    continue
                break
            while True:
                raw_deadline = input("Nhập hạn chót (DD/MM/YYYY): ")
                deadline = raw_deadline.strip().split()[0] if raw_deadline.strip() else ""
                if not deadline:
                    print("[LOI] LỖI: Hạn chót không được để trống")
                    continue
                if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", deadline):
                    print("[LOI] LỖI: Định dạng hạn chót phải là DD/MM/YYYY (ví dụ 01/01/2020)")
                    continue
                try:
                    datetime.strptime(deadline, "%d/%m/%Y")
                except ValueError:
                    print("[LOI] LỖI: Ngày không hợp lệ")
                    continue
                if datetime.strptime(deadline, "%d/%m/%Y").date() <= datetime.now().date():
                    print("[LOI] LỖI: Hạn chót phải là ngày trong tương lai (không được là hôm nay)")
                    continue
                break
            while True:
                priority = input("Nhập độ ưu tiên (Cao/Trung bình/Thấp): ")
                if priority not in TaskManager.PRIORITY_VALUES:
                    print(f"[LOI] LỖI: Độ ưu tiên phải là một trong {TaskManager.PRIORITY_VALUES}")
                    continue
                break
            # Add the task after all inputs are validated
            try:
                task = manager.add_task(name, deadline, priority)
                print(f"[OK] Đã thêm công việc \"{task.name}\"")
            except ValueError as e:
                print(f"[LOI] LỖI: {e}")
        elif choice_num == 2:
            tasks = manager.list_tasks()
            _print_tasks(tasks)
        elif choice_num == 3:
            identifier = input("Nhập STT hoặc tên công việc: ")
            # Try integer first
            try:
                ident = int(identifier)
            except ValueError:
                ident = identifier.strip()
            try:
                task = manager.mark_complete(ident)
                print(f"[OK] Đã đánh dấu hoàn thành \"{task.name}\"")
            except LookupError as e:
                print(f"[LOI] {e}")
        elif choice_num == 4:
            identifier = input("Nhập STT hoặc tên công việc: ")
            try:
                ident = int(identifier)
            except ValueError:
                ident = identifier.strip()
            try:
                task = manager.delete_task(ident)
                print(f"[OK] Đã xóa công việc \"{task.name}\"")
            except LookupError as e:
                print(f"[LOI] {e}")
        elif choice_num == 5:
            # Export tasks to CSV for opening in WPS Sheets
            _export_to_csv(manager.list_tasks())
            print("[OK] Đã xuất danh sách công việc ra tasks.csv")
        elif choice_num == 6:
            print("[OK] Tạm biệt!")
            break
        else:
            print("[LOI] Lựa chọn không hợp lệ")


if __name__ == "__main__":
    main()

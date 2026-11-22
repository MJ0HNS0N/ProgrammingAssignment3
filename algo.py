import argparse
from copy import copy

class Task:
    def __init__(self, task_name: str, task_deadline: int, task_wcets: list[str], task_frequency: int = 1188) -> None:
        """
        Class constructor for Task object
        """
        
        self.name: str = task_name
        self.deadline: int = task_deadline
        self.wcets: list[int] = []
        for wcet in task_wcets:
            self.wcets.append(int(wcet))
        
        self.frequency: int = task_frequency # denotes current frequency of task
        self.remain: int = self.get_wcet() # denotes remaining time for task to complete
    
    def get_wcet(self, frequency: int | None = None) -> int:
        """
        Get worst case execution time based on frequency
        Pass it a frequency to get the wcet for that frequency or it will just give wcet for self.frequency
        """
        freq = frequency if frequency is not None else self.frequency
        index: int = 0
        
        match(freq):
            case 1188: index = 0
            case 918: index = 1
            case 648: index = 2
            case 384: index = 3

        return self.wcets[index]

    def __str__(self) -> str:
        """
        Return a string representation of the task
        """
        return f"Name: {self.name}, Deadline: {self.deadline}, Remaining: {self.remain}"
        

def parse_cli() -> argparse.Namespace:
    """
    Parses command line arguments using argparse library
    """
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument("infile")
    parser.add_argument("schedule", choices=["EDF", "RM"])
    parser.add_argument("ee", nargs="?", choices=["EE"], default=None) # EE is optional

    return parser.parse_args()

def min_remaining(tasks: list[Task]) -> Task:
    """
    Get the task with the lowest remaining time
    """
    low_task: Task = tasks[0]
    
    for task in tasks:
        if task.remain < low_task.remain:
            low_task = task
    
    return low_task

def max_remaining(tasks: list[Task]) -> Task:
    """
    Get the task with the highest deadline
    """
    high_task: Task = tasks[0]
    
    for task in tasks:
        if task.remain > high_task.remain:
            high_task = task
    
    return high_task

def run_RM(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm
    """
    schedule: list[Task | None] = []
    rm_tasks: list[Task] = sorted(tasks, key=lambda x: x.deadline) # sort tasks by deadline
    queue: list[Task] = []
    task: Task = rm_tasks[0]
    schedule.append(task)
    event: bool = False
    
    for tsk in rm_tasks:
        tsk.frequency = 1188
        tsk.remain = tsk.get_wcet()
    
    for t in range(0, t_exec):
        event = False
        for tsk in rm_tasks:
            if t == 0 or t % tsk.deadline == 0:
                new_job = copy(tsk)
                new_job.remain = new_job.get_wcet()
                queue.append(new_job)
                event = True

            queue.sort(key=lambda x: x.deadline) # sort queue by deadline (lowest first)
            
            if len(queue) and task != queue[0]:
                task = queue[0] # get task with highest priority (lowest deadline)
                event = True
        
        if task.remain > 1:
            task.remain -= 1
        elif len(queue) > 0:
            task.remain = 0
            task = queue[0]
            queue.remove(task)
            event = True
        
        if t == 0 or event:
            print(f"t = {t}, task = {task}, queue = {[tsk.name for tsk in queue]}")
        

def run_RM_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm with energy efficiency
    """
    pass

def run_EDF(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Earliest Deadline First scheduling algorithm
    """
    pass

def run_EDF_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Earliest Deadline First scheduling algorithm with energy efficiency
    """
    pass

def main() -> int:
    """
    Main execution
    """
    
    # Parse command line arguments
    args = parse_cli()

    #print("Input file:", args.infile)
    #print("Scheduling:", args.schedule)
    #print("Energy efficient:", args.ee is not None)
    
    # Parse input file
    table: list = []
    with open(args.infile, "r") as f:
        for line in f:
            table.append(line.split())
    
    # Parse first row
    num_tasks: int = int(table[0][0])
    t_exec: int = int(table[0][1])
    p_cpu: list[int] = [] # p_cpu goes power at [ 1188 Mhz, 918 Mhz, 648 Mhz, 384 Mhz ]
    for pwr in table[0][2:]:
        p_cpu.append(int(pwr))
    
    # Parse tasks (row 2+)
    tasks: list[Task] = []
    for t in table[1:]:
        tasks.append(Task(t[0], int(t[1]), t[2:]))
        
    run_RM(tasks, p_cpu, t_exec)
    
    """
    if args.schedule == "RM":
        if args.ee is not None:
            run_RM_EE(tasks, p_cpu, t_exec)
        else:
            run_RM(tasks, p_cpu, t_exec)
    else:
        if args.ee is not None:
            run_EDF_EE(tasks, p_cpu, t_exec)
        else:
            run_EDF(tasks, p_cpu, t_exec)
    """

    #print("Table:\n", table)
    #print(f"num_tasks = {num_tasks}")
    #print(f"t_exec = {t_exec}")
    #print(f"p_cpu = {p_cpu}")
    #print("Tasks:\n")
    #for task in tasks:
    #    print(task)
    
    return 0

if __name__ == "__main__":
    main()
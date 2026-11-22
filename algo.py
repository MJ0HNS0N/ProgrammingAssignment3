import argparse

class Task:
    def __init__(self, task_name: str, task_deadline: int, task_wcets: list[str]) -> None:
        """
        Class constructor for Task object
        """
        
        self.name: str = task_name
        self.deadline: int = task_deadline
        self.wcets: list[int] = []
        for wcet in task_wcets:
            self.wcets.append(int(wcet))
    
    def get_wcet_at(self, frequency: int) -> int:
        """
        Get worst case execution time based on frequency
        """
        
        index: int = 0
        
        match(frequency):
            case 1188: index = 0
            case 918: index = 1
            case 648: index = 2
            case 384: index = 3

        return self.wcets[index]

    def __str__(self) -> str:
        """
        Return a string representation of the task
        """
        return f"Name: {self.name}\nDeadline: {self.deadline}\nWCETs: {self.wcets}"
        

def parse_cli() -> argparse.Namespace:
    """
    Parses command line arguments using argparse library
    """
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument("infile")
    parser.add_argument("schedule", choices=["EDF", "RM"])
    parser.add_argument("ee", nargs="?", choices=["EE"], default=None) # EE is optional

    return parser.parse_args()

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

def run_RM(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm
    """
    pass

def run_RM_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm with energy efficiency
    """
    pass

def main() -> int:
    """
    Main execution
    """
    
    # Parse command line arguments
    args = parse_cli()

    print("Input file:", args.infile)
    print("Scheduling:", args.schedule)
    print("Energy efficient:", args.ee is not None)
    
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
        
    print("Table:\n", table)
    print(f"num_tasks = {num_tasks}")
    print(f"t_exec = {t_exec}")
    print(f"p_cpu = {p_cpu}")
    print("Tasks:\n")
    for task in tasks:
        print(task)
    
    return 0

if __name__ == "__main__":
    main()
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
        
        self.release_time: int = 0
        self.absolute_deadline: int = task_deadline
        self.miss_reported: bool = False # save if there was a deadline miss
    
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

def run_RM(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Rate Monotonic scheduling at 1188 MHz,
    followed by segment and energy calculation.
    """

    rm_tasks = sorted(tasks, key=lambda x: x.deadline)
    queue: list[Task] = []
    task: Task | None = None

    frequency = 1188
    active_power = p_cpu[0]
    idle_power = p_cpu[4]

    # one entry per time unit
    schedule: list[tuple[str, str, int]] = []

    for t in range(t_exec):
        # Release new jobs
        for original_task in rm_tasks:
            if t == 0 or t % original_task.deadline == 0:
                new_job = copy(original_task)

                new_job.release_time = t
                new_job.absolute_deadline = t + original_task.deadline
                new_job.miss_reported = False

                new_job.frequency = frequency
                new_job.remain = new_job.get_wcet()

                queue.append(new_job)
        
        # check for deadline misses (I keep getting one for input1)
        for queued_job in queue:
            if (t >= queued_job.absolute_deadline and queued_job.remain > 0 and not queued_job.miss_reported):
                print(f"DEADLINE MISS: {queued_job.name} released at {queued_job.release_time}, deadline {queued_job.absolute_deadline}, remaining {queued_job.remain}")
                queued_job.miss_reported = True

        queue.sort(key=lambda x: x.deadline) # sort lowest deadline first

        # update task to the one with the earliest deadline
        if queue:
            if task is None or task not in queue or task.deadline > queue[0].deadline: # just being careful here
                task = queue[0]

        # log task name, frequency, and power consumption
        if task is None:
            schedule.append(("IDLE", "IDLE", idle_power))
        else:
            schedule.append((task.name, str(frequency), active_power))

        # execute task for 1 time unit
        if task is not None:
            task.remain -= 1

            # job has completed
            if task.remain == 0:
                if task in queue:
                    queue.remove(task)

                # select next task
                queue.sort(key=lambda x: x.deadline)
                task = queue[0] if queue else None

    # combine consecutive identical schedule entries
    start_time = 0
    total_energy = 0.0
    idle_time = 0

    for index in range(1, len(schedule) + 1):
        segment_finished = (
            index == len(schedule)
            or schedule[index] != schedule[start_time]
        )

        if segment_finished:
            name, freq, power = schedule[start_time]
            duration = index - start_time
            energy = power * duration / 1000

            if name == "IDLE":
                print(f"{start_time} IDLE IDLE {duration} {energy:.3f}J")
                idle_time += duration
            else:
                print(f"{start_time} {name} {freq} {duration} {energy:.3f}J")

            total_energy += energy
            start_time = index

    idle_percentage = idle_time / t_exec * 100

    # log to console
    print(f"Total energy: {total_energy:.3f}J")
    print(f"Percentage idle: {idle_percentage:.2f}%")
    print(f"Total execution time: {t_exec}s")
        
def choose_frequency(task, current_time):
    time_left = task.deadline - current_time

    for frequency in [384, 648, 918, 1188]:
        wcet = task.get_wcet(frequency)

        if wcet <= time_left:
            return frequency

    return 1188

def run_RM_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm with energy efficiency
    """
    frequencies: list[int] = [384, 648, 918, 1188]
    rm_tasks: list[Task] = sorted(tasks, key=lambda x: x.deadline) # sort tasks by deadline
    queue: list[Task] = []
    task: Task | None = rm_tasks[0]
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
        
        if task and task.remain > 1:
            task.remain -= 1
        elif len(queue) > 0:
            task.remain = 0
            task = queue[0]
            queue.remove(task)
            event = True
        
        if t == 0 or event:
            print(f"t = {t}, task = {task}, queue = {[tsk.name for tsk in queue]}")
    

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
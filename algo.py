import argparse
from copy import copy
from math import ceil

# Using a constant since I need these everywhere
FREQUENCIES = [384, 648, 918, 1188]

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

def get_power(frequency: int, p_cpu: list[int]) -> int:
    """
    Return active power for a CPU frequency
    """
    match(frequency):
        case 1188: return p_cpu[0]
        case 918: return p_cpu[1]
        case 648: return p_cpu[2]
    return p_cpu[3]

def choose_rm_frequency(new_job: Task, current_time: int, queue: list[Task], rm_tasks: list[Task]) -> int:
    """
    Helper fxn for RM to choose a lower frequency only if the total task utilization < 1
    """

    frequencies = [384, 648, 918, 1188]

    for frequency in frequencies:
        utilization = 0.0

        for original_task in rm_tasks:
            if original_task.name == new_job.name:
                wcet = new_job.get_wcet(frequency)
            else:
                # Keep other tasks at maximum frequency for safety
                wcet = original_task.get_wcet(1188)

            utilization += wcet / original_task.deadline

        if utilization <= 1.0:
            return frequency

    return 1188 # default to max freq

def run_RM(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Rate Monotonic scheduling at 1188 MHz followed by segment and energy calculation
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
        segment_finished = (index == len(schedule) or schedule[index] != schedule[start_time])

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

def run_RM_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> None:
    """
    Run Rate Monotonic scheduling algorithm with energy efficiency
    """
    rm_tasks = sorted(tasks, key=lambda x: x.deadline)
    queue: list[Task] = []
    task: Task | None = None

    idle_power = p_cpu[4]

    # one entry per time unit (name, freq, power)
    schedule: list[tuple[str, str, int]] = []

    for t in range(t_exec):

        # new job logic
        for original_task in rm_tasks:
            if t == 0 or t % original_task.deadline == 0:
                new_job = copy(original_task)

                new_job.release_time = t
                new_job.absolute_deadline = (t + original_task.deadline)
                new_job.miss_reported = False

                new_job.frequency = choose_rm_frequency(new_job, t, queue, rm_tasks)
                new_job.remain = new_job.get_wcet()

                queue.append(new_job)

        # check for deadline misses
        for queued_job in queue:
            if (t >= queued_job.absolute_deadline and queued_job.remain > 0 and not queued_job.miss_reported):
                print(f"DEADLINE MISS: {queued_job.name} released at {queued_job.release_time}, deadline {queued_job.absolute_deadline}, remaining {queued_job.remain}")
                queued_job.miss_reported = True

        # sort by deadlines, lowest first
        queue.sort(key=lambda x: x.deadline)

        # go to highest priority
        if queue:
            if (task is None or task not in queue or task.deadline > queue[0].deadline):
                task = queue[0]

        # log task to console, save to schedule
        if task is None:
            schedule.append(("IDLE", "IDLE", idle_power))
        else:
            power = get_power(task.frequency, p_cpu)
            schedule.append((task.name, str(task.frequency),power))

        # execute task for one time unit
        if task is not None:
            task.remain -= 1

            # job completed
            if task.remain == 0:
                if task in queue:
                    queue.remove(task)

                queue.sort(key=lambda x: x.deadline)
                task = queue[0] if queue else None

    # combine back to back identical entries
    start_time = 0
    total_energy = 0.0
    idle_time = 0

    for index in range(1, len(schedule) + 1):
        segment_finished = (index == len(schedule) or schedule[index] != schedule[start_time])

        if segment_finished:
            name, frequency, power = schedule[start_time]
            duration = index - start_time
            energy = power * duration / 1000

            if name == "IDLE":
                print(f"{start_time} IDLE IDLE {duration} {energy:.3f}J")
                idle_time += duration
            else:
                print(f"{start_time} {name} {frequency} {duration} {energy:.3f}J")

            total_energy += energy
            start_time = index

    # final calculations and logging
    idle_percentage = idle_time / t_exec * 100

    print(f"Total energy: {total_energy:.3f}J")
    print(f"Percentage idle: {idle_percentage:.2f}%")
    print(f"Total execution time: {t_exec}s")
    

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
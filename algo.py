import argparse

from anyio import current_time

from copy import deepcopy

FREQUENCY_OPTIONS = [1188, 918, 648, 384]
MAX_FREQUENCY = FREQUENCY_OPTIONS[0]
EPSILON = 1e-8


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

def run_EDF(tasks: list[Task], p_cpu: list[int], t_exec: int) -> list[list]:
    """
    Run Earliest Deadline First scheduling algorithm
    """

    time = 1
    time_idle = 0
    total_energy = 0.0
    #queue = [[task names],[arrival time],[deadline],[remaining execution time],[ready_status]]
    queue = [[],[],[],[],[],[]]
    significant_times = {t_exec}

    # Set up initial queue with tasks at max CPU frequency (1188 MHz)
    # Separate from task object to avoid modifying the original task objects
    for task in tasks:
        period = task.deadline  

        for arrival_time in range(0, t_exec, period):
            deadline = arrival_time + period
            execution_time = task.get_wcet_at(1188)
        
            queue[0].append(task.name)
            queue[1].append(arrival_time)
            queue[2].append(deadline)
            queue[3].append(execution_time)
            queue[4].append(False)

            significant_times.add(arrival_time)

    # Schedule logging array to printout afterwards
    schedule = [[]]

    while time < t_exec:

        # set ready status for each task in the queue based on current time and set arrival time
        for i in range(len(queue[1])):
            queue[4][i] = queue[1][i] <= time

        # if nothing in queue, set up idle time until a task is added to the queue
        if not any(queue[4]):  # If no tasks are ready
            next_time = min(t for t in significant_times if t > time)
            idle_segment = next_time - time
            time_idle += idle_segment

            schedule[0].append([time, "IDLE", "IDLE", idle_segment, idle_segment*p_cpu[-1]*0.001])
            total_energy += idle_segment*p_cpu[-1]*0.001
            time = next_time
            continue

        task_to_run = min((i for i, ready in enumerate(queue[4]) if ready),
                            key=lambda i: queue[2][i]
                        )

        next_time = min(t for t in significant_times if t > time)
        execution_time = 0
        if (time + queue[3][task_to_run]) > next_time:
            # If the task cannot finish before the execution time limit, run it for the remaining time
            execution_time = next_time - time
            queue[3][task_to_run] -= execution_time
        else:
            # finish task and remove it from the queue
            execution_time = queue[3][task_to_run]

            #check if task missed its deadline
            if queue[2][task_to_run] < execution_time + time:
                print(f"Task {queue[0][task_to_run]} missed its deadline at time {time + execution_time}.")

        if schedule[0][-1][1] == queue[0][task_to_run] and schedule[0][-1][2] == 1188:
            # If the last scheduled task is the same as the current task, merge the time segments
            schedule[0][-1][3] += execution_time
            schedule[0][-1][4] += execution_time*p_cpu[0]*0.001
        else:
            schedule[0].append([time, queue[0][task_to_run], 1188, execution_time, execution_time*p_cpu[0]*0.001])

        total_energy += execution_time*p_cpu[0]*0.001

        # remove task from queue
        for item in queue:
            item.pop(task_to_run)

        time += execution_time

    print (f"Total idle time: {time_idle}")
    print (f"Total energy consumption: {total_energy}")
    print (f"Total execution time: {time}")
    print (f"Percentage of idle time: {time_idle/time*100}%")
    return schedule

def run_EDF_EE(tasks: list[Task], p_cpu: list[int], t_exec: int) -> tuple[list[list], float]:
    """
    Run Earliest Deadline First scheduling with energy-efficient
    frequency selection.

    """

    time = 1.0
    total_energy = 0.0
    time_idle = 0.0

    queue = []

    # t_exec is the final time slot, so the simulation ends after t_exec
    end_time = float(t_exec)

    # Used to identify arrival times
    significant_times = {t_exec}

    # Create every periodic task instance
    for task in tasks:
        period = task.deadline

        for arrival_time in range(1, t_exec + 1, period):
            deadline = arrival_time + period - 1

            job = Task(task.name, deadline, deepcopy(task.wcets))

            job.arrival_time = arrival_time
            job.ready_status = False

            # Fraction of the original task that remains
            job.remaining_fraction = 1.0

            queue.append(job)
            significant_times.add(arrival_time)

    schedule = [[]]

    while time < end_time:

        # Update ready status
        for job in queue:
            job.ready_status = (job.arrival_time <= time and job.remaining_fraction > EPSILON)

        ready_task_indexes = [i for i, job in enumerate(queue) if job.ready_status]

        # No task is ready: run idle until the next arrival
        if not ready_task_indexes:
            future_times = [event_time for event_time in significant_times if event_time > time]

            if not future_times:
                break

            next_time = min(future_times)
            idle_time = min(next_time - time, end_time - time)

            if idle_time <= EPSILON:
                break

            # Assumes p_cpu[-1] is idle power
            idle_energy = idle_time * p_cpu[-1] * 0.001

            schedule[0].append([time, "IDLE", "IDLE", idle_time, idle_energy])

            time_idle += idle_time
            total_energy += idle_energy
            time += idle_time
            continue

        # choose the ready task with the earliest deadline
        task_to_run = min(ready_task_indexes, key=lambda i: queue[i].deadline)

        # Select the lowest-energy feasible frequency
        frequency = find_optimal_frequency(queue, task_to_run,time, p_cpu)

        # Find the next arrival or simulation endpoint
        future_times = [event_time for event_time in significant_times if event_time > time]

        next_time = min(future_times + [end_time])

        job = queue[task_to_run]

        # Remaining execution time at the selected frequency
        full_wcet_at_frequency = job.get_wcet_at(frequency)
        remaining_time = (job.remaining_fraction * full_wcet_at_frequency)

        # Run either until completion or the next arrival
        execution_time = min(remaining_time, next_time - time, end_time - time)

        if execution_time <= EPSILON:
            break

        # Update the fraction of work remaining
        work_completed_fraction = (execution_time / full_wcet_at_frequency)

        job.remaining_fraction -= work_completed_fraction
        job.remaining_fraction = max(0.0, job.remaining_fraction)

        # Calculate energy
        frequency_index = FREQUENCY_OPTIONS.index(frequency)
        energy = (execution_time * p_cpu[frequency_index] * 0.001)

        schedule[0].append([time, job.name, frequency, execution_time, energy])

        total_energy += energy

        completion_time = time + execution_time
        task_finished = job.remaining_fraction <= EPSILON

        # Only check the deadline after the task finishes
        if task_finished:
            # Since deadlines are final slot numbers,
            # deadline + 1 is the completion boundary.
            if completion_time > job.deadline + 1:
                print(
                    f"Task {job.name} missed its deadline "
                    f"at time {completion_time} with deadline {job.deadline + 1} and remaining fraction {job.remaining_fraction}."
                )

        time += execution_time

        # Do not remove a task if it was only partially executed
        if task_finished:
            queue.pop(task_to_run)

    print (f"Total idle time: {time_idle}")
    print (f"Total energy consumption: {total_energy}")
    print (f"Total execution time: {time}")
    print (f"Percentage of idle time: {time_idle/time*100}%")
    return schedule, total_energy


def find_optimal_frequency(
    queue: list[Task],
    task_index: int,
    time: float,
    p_cpu: list[int]
) -> int:
    """
    Choose the feasible frequency with the lowest energy.

    """

    ready_task_indexes = [
        i for i, job in enumerate(queue)
        if (
            job.ready_status
            and job.remaining_fraction > EPSILON
        )
    ]

    # EDF order
    ready_task_indexes.sort(
        key=lambda i: queue[i].deadline
    )

    feasible_options = []

    for frequency_index, frequency in enumerate(
        FREQUENCY_OPTIONS
    ):
        cumulative_time = 0.0
        is_feasible = True

        for i in ready_task_indexes:
            job = queue[i]

            if i == task_index:
                test_frequency = frequency
            else:
                test_frequency = MAX_FREQUENCY

            remaining_time = (
                job.remaining_fraction
                * job.get_wcet_at(test_frequency)
            )

            cumulative_time += remaining_time

            # Deadline is the final slot, so use deadline + 1
            deadline_boundary = job.deadline + 1

            if time + cumulative_time > deadline_boundary:
                is_feasible = False
                break

        if is_feasible:
            current_job = queue[task_index]

            remaining_time = (
                current_job.remaining_fraction
                * current_job.get_wcet_at(frequency)
            )

            energy = (
                remaining_time
                * p_cpu[frequency_index]
                * 0.001
            )

            feasible_options.append(
                (energy, frequency)
            )

    # If no frequency is feasible, use maximum frequency
    if not feasible_options:
        return MAX_FREQUENCY

    # Choose frequency with minimum energy
    _, best_frequency = min(
        feasible_options,
        key=lambda option: option[0]
    )

    return best_frequency

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

    schedule = run_EDF_EE(tasks, p_cpu, t_exec)

    print("\nSchedule:\n")
    for entry in schedule[0]:
        print(entry)
    return 0

if __name__ == "__main__":
    main()
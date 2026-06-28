# Assembly and Operating Systems: A Deep Dive Guide

This guide provides a comprehensive overview of low-level systems programming, focusing on Assembly language (both x86_64 and ARM64), CPU architecture, and Operating System mechanics.

## Table of Contents
1. [Introduction to Assembly Language](#1-introduction-to-assembly-language)
2. [x86_64 Architecture and Assembly](#2-x86_64-architecture-and-assembly)
3. [ARM64 (Apple Silicon M-Series) Architecture and Assembly](#3-arm64-architecture-and-assembly)
4. [CPU Caching Pipelines and Memory Hierarchy](#4-cpu-caching-pipelines-and-memory-hierarchy)
5. [Kernel Space vs. User Space & Context Switching](#5-kernel-space-vs-user-space--context-switching)
6. [POSIX System Calls](#6-posix-system-calls)

---

## 1. Introduction to Assembly Language

Assembly language is the lowest human-readable programming language, providing direct control over the CPU's instructions and registers. Unlike high-level languages (like C, Python, or Rust) which are compiled into machine code, assembly language uses mnemonics that map almost one-to-one with machine code instructions.

### Key Concepts
*   **Registers:** Small, extremely fast storage locations directly on the CPU.
*   **Instructions:** Commands the CPU executes (e.g., `mov`, `add`, `jmp`).
*   **Memory Addressing:** Methods to specify memory locations (immediate, register, direct, indirect).
*   **Stack:** A LIFO (Last-In, First-Out) data structure used for function calls, local variables, and control flow.

---

## 2. x86_64 Architecture and Assembly

The x86_64 (or AMD64) architecture is the dominant 64-bit instruction set architecture (ISA) for desktop and server processors (Intel and AMD). It is a Complex Instruction Set Computer (CISC) architecture.

### General Purpose Registers (GPRs)
*   **RAX:** Accumulator (often used for function return values).
*   **RBX:** Base register.
*   **RCX:** Counter register (used in loops and string operations).
*   **RDX:** Data register.
*   **RSI:** Source index (string operations).
*   **RDI:** Destination index (string operations, first function argument).
*   **RSP:** Stack pointer (points to the top of the stack).
*   **RBP:** Base pointer (points to the base of the current stack frame).
*   **R8 - R15:** Additional general-purpose registers.

### Syntax (AT&T vs. Intel)
There are two main syntax styles for x86 assembly. Intel syntax is generally preferred for readability.

*   **Intel Syntax:** `instruction destination, source` (e.g., `mov rax, 1`)
*   **AT&T Syntax:** `instruction source, destination` (e.g., `movq $1, %rax`)

### Common Instructions
*   `mov dest, src`: Move data from `src` to `dest`.
*   `add dest, src`: Add `src` to `dest`.
*   `sub dest, src`: Subtract `src` from `dest`.
*   `cmp arg1, arg2`: Compare `arg1` and `arg2` (sets flags).
*   `jmp label`: Unconditional jump.
*   `je / jne label`: Jump if equal / not equal (based on previous `cmp`).
*   `call function`: Push RIP (instruction pointer) to stack and jump to function.
*   `ret`: Pop RIP from stack and return to caller.

### Example: Hello World (Linux syscall)
```nasm
global _start

section .data
    msg db 'Hello, x86_64!', 0Ah
    len equ $ - msg

section .text
_start:
    ; write(1, msg, len)
    mov rax, 1      ; syscall number for write
    mov rdi, 1      ; file descriptor 1 (stdout)
    mov rsi, msg    ; pointer to message
    mov rdx, len    ; message length
    syscall         ; invoke syscall

    ; exit(0)
    mov rax, 60     ; syscall number for exit
    xor rdi, rdi    ; exit code 0
    syscall
```

---

## 3. ARM64 (Apple Silicon M-Series) Architecture and Assembly

ARM64 (also known as AArch64) is a Reduced Instruction Set Computer (RISC) architecture. It is highly power-efficient and is the architecture behind Apple's M-series chips (M1, M2, M3) and modern mobile devices.

### General Purpose Registers
ARM64 has 31 general-purpose registers (`x0` to `x30`), each 64 bits wide.

*   **x0 - x7:** Argument and return value registers.
*   **x8:** Indirect result location register.
*   **x9 - x15:** Caller-saved temporary registers.
*   **x16 - x17:** Intra-procedure-call temporary registers (often used by linkers).
*   **x18:** Platform register.
*   **x19 - x28:** Callee-saved registers.
*   **x29 (FP):** Frame Pointer.
*   **x30 (LR):** Link Register (stores the return address for function calls).
*   **SP:** Stack Pointer (not one of the general-purpose registers, though sometimes aliased).
*   **XZR (WZR):** Zero register (always reads as 0, discards writes).

### Common Instructions
Unlike CISC x86_64, RISC architectures typically use load/store operations exclusively for memory access; data must be moved into registers before manipulation.

*   `mov dest, src`: Move data into register.
*   `ldr dest, [addr]`: Load data from memory `addr` into `dest`.
*   `str src, [addr]`: Store data from `src` into memory `addr`.
*   `add dest, src1, src2`: `dest = src1 + src2`.
*   `cmp reg1, reg2`: Compare registers.
*   `b label`: Unconditional branch (jump).
*   `bl label`: Branch with Link (calls a function, stores return address in `x30`/`LR`).
*   `ret`: Return (jumps to address in `x30`/`LR`).

### Calling Convention (Apple Silicon macOS)
*   Arguments 1-8 are passed in `x0` - `x7`.
*   Return values are in `x0`.
*   Syscall numbers are placed in `x16`.
*   Syscalls are invoked using the `svc 0` (Supervisor Call) instruction.

### Example: Hello World (macOS syscall)
```assembly
.global _main
.align 2

.data
msg: .ascii "Hello, ARM64!\n"
len = . - msg

.text
_main:
    // write(1, msg, len)
    mov x0, 1           // file descriptor 1 (stdout)
    adrp x1, msg@PAGE   // load upper bits of msg address
    add x1, x1, msg@PAGEOFF // add lower 12 bits
    mov x2, len         // message length
    mov x16, 4          // syscall number for write (macOS)
    svc 0               // invoke syscall

    // exit(0)
    mov x0, 0           // exit code 0
    mov x16, 1          // syscall number for exit (macOS)
    svc 0
```

---

## 4. CPU Caching Pipelines and Memory Hierarchy

Modern CPUs are significantly faster than main memory (RAM). To bridge this gap, CPUs use an intricate memory hierarchy and instruction pipelining.

### Memory Hierarchy
1.  **Registers:** Immediate access (0 cycles latency).
2.  **L1 Cache (Instruction & Data):** Small, extremely fast cache built into each core (1-3 cycles latency).
3.  **L2 Cache:** Larger cache, often dedicated to a specific core or shared between a pair (10-14 cycles latency).
4.  **L3 Cache:** Large cache shared across all cores on the die (~30-50 cycles latency).
5.  **Main Memory (RAM):** Large, but slow (~100+ cycles latency).
6.  **Storage (SSD/HDD):** Persistent, very slow (thousands of cycles).

### Cache Lines and Spatial Locality
Memory is not loaded byte-by-byte into the cache. It is loaded in "cache lines" (typically 64 bytes). 
*   **Spatial Locality:** If you access memory at address `X`, you are likely to access `X+1` soon. Loading a full cache line optimizes for this.
*   **False Sharing:** Occurs when multiple threads modify independent variables residing on the same cache line, causing unnecessary cache invalidations and degrading performance.

### CPU Pipelining
Execution of an instruction is broken down into stages (e.g., Fetch, Decode, Execute, Memory Access, Write-Back).
Pipelining allows multiple instructions to be processed simultaneously at different stages.

### Hazards in Pipelining
1.  **Data Hazards:** Instruction B depends on the result of Instruction A, which hasn't finished. (Resolved via forwarding/bypassing or stalling).
2.  **Control Hazards (Branching):** The CPU doesn't know which instruction to fetch next until a conditional branch is resolved. (Resolved via Branch Prediction).
3.  **Structural Hazards:** Hardware resources are insufficient to support all combinations of instructions in the pipeline.

### Branch Prediction and Speculative Execution
Modern CPUs attempt to guess the outcome of branches (`if` statements). If they guess correctly, execution continues without stalling. If they guess incorrectly, the pipeline is flushed (a costly penalty). Speculative execution executes instructions along the predicted path before the branch is fully resolved.

---

## 5. Kernel Space vs. User Space & Context Switching

Modern operating systems divide memory into two distinct areas for security and stability.

### User Space
*   Where normal applications and user programs run (e.g., web browsers, your text editor, standard user processes).
*   Limited privileges: Cannot directly access hardware, physical memory, or restricted CPU instructions.
*   Must request services from the kernel via System Calls.
*   A crash here usually only kills the specific process.

### Kernel Space
*   Where the core operating system (the kernel) executes.
*   Highest privilege level (Ring 0 on x86).
*   Direct access to all hardware, CPU instructions, and memory.
*   A crash here causes a system-wide failure (Kernel Panic / Blue Screen of Death).

### Context Switching
A context switch is the process of storing the state of a currently running process (or thread) so that it can be paused, and restoring the state of another process so it can resume execution.

**When does it happen?**
1.  **Multitasking:** The OS scheduler preempts a process to give CPU time to another process.
2.  **Interrupts:** Hardware (like a keyboard press or disk read completion) interrupts the CPU, forcing it to handle the event in the kernel.
3.  **System Calls:** A user-space program invokes a syscall, triggering a transition to kernel space.

**The Context Switch Process (Simplified):**
1.  **Save State:** The CPU saves the current state (registers, program counter, stack pointer, page tables) of Process A into its Process Control Block (PCB).
2.  **Mode Switch:** Transition from User Mode to Kernel Mode (if necessary).
3.  **Scheduler Decision:** The OS scheduler selects Process B to run next.
4.  **Restore State:** Load the saved state from Process B's PCB into the CPU registers.
5.  **Mode Switch:** Transition back to User Mode.
6.  **Resume:** Process B resumes execution.

*Note: Context switches are computationally expensive due to register saving/restoring and, crucially, the flushing of the Translation Lookaside Buffer (TLB) and potential cache invalidations.*

---

## 6. POSIX System Calls

POSIX (Portable Operating System Interface) is a family of standards specified by the IEEE for maintaining compatibility between operating systems. System calls (syscalls) are the fundamental interface between user-space applications and the kernel.

### The Mechanism
1.  The user application places arguments into specific registers (defined by the architecture's calling convention).
2.  The application places the syscall number into a specific register (e.g., `rax` on x86_64, `x16` on macOS ARM64).
3.  The application executes a special hardware instruction (`syscall` on x86_64, `svc 0` on ARM64).
4.  The CPU traps into kernel mode, looks up the syscall number in the Syscall Table, and executes the corresponding kernel function.
5.  The kernel returns the result (usually in `rax` or `x0`).

### Common POSIX Syscalls

#### File Operations
*   `open(const char *pathname, int flags)`: Opens a file and returns a File Descriptor (FD).
*   `read(int fd, void *buf, size_t count)`: Reads `count` bytes from `fd` into `buf`.
*   `write(int fd, const void *buf, size_t count)`: Writes `count` bytes from `buf` to `fd`.
*   `close(int fd)`: Closes a file descriptor.
*   `lseek(int fd, off_t offset, int whence)`: Repositions the file offset.

#### Process Control
*   `fork()`: Creates a new child process by duplicating the calling process.
*   `execve(const char *pathname, char *const argv[], char *const envp[])`: Replaces the current process image with a new executable.
*   `waitpid(pid_t pid, int *status, int options)`: Suspends execution until a child process terminates.
*   `exit(int status)`: Terminates the calling process.

#### Memory Management
*   `mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset)`: Maps files or devices into memory, or allocates anonymous memory (often how `malloc` gets memory from the OS for large allocations).
*   `munmap(void *addr, size_t length)`: Unmaps a memory region.
*   `mprotect(void *addr, size_t len, int prot)`: Sets protection on a region of memory (e.g., making it read-only or executable).

#### Inter-Process Communication (IPC) & Networking
*   `pipe(int pipefd[2])`: Creates a unidirectional data channel.
*   `socket(int domain, int type, int protocol)`: Creates an endpoint for communication.
*   `bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen)`: Assigns an address to a socket.
*   `listen(int sockfd, int backlog)`: Marks a socket as passive (listening for connections).
*   `accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen)`: Accepts a connection on a listening socket.
*   `connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen)`: Initiates a connection on a socket.

Understanding these concepts provides the foundation for systems programming, performance optimization, and reverse engineering.

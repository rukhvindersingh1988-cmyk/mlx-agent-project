# Modern C++ Game Engine Architecture Deep Dive

Welcome to the definitive guide on building high-performance, modern game engines using C++20/C++23. This guide covers the essential paradigms shift from traditional object-oriented architectures to data-oriented designs, modern C++ features, memory management strategies, and explicit graphics API abstractions.

## 1. Modern C++20/23 Features for Game Engines

Game engine development demands absolute control over hardware while maintaining a high level of abstraction for game-play programmers. Modern C++ provides features that allow us to achieve zero-overhead abstractions.

### 1.1 Concepts (C++20)
Concepts replace complex SFINAE (Substitution Failure Is Not An Error) with clear, readable constraints on template parameters. They improve compile times and provide readable error messages.

```cpp
template <typename T>
concept Renderable = requires(T a) {
    { a.draw() } -> std::same_as<void>;
    { a.get_bounding_box() } -> std::convertible_to<AABB>;
};

void submit_to_renderer(Renderable auto& object) {
    object.draw();
}
```

### 1.2 Coroutines (C++20)
Coroutines are stackless and perfect for asynchronous tasks such as asset loading, streaming, or even scripting gameplay logic over multiple frames.

```cpp
Task<void> load_level_async(std::string path) {
    LevelData data = co_await io_system.read_file_async(path);
    co_await resource_manager.upload_textures_to_gpu(data.textures);
    scene_graph.build(data.nodes);
}
```

### 1.3 Modules (C++20)
Header files and macro pollution have been a bane for compile times in large engines. C++20 Modules solve this by parsing code once and exporting only what is needed.

```cpp
export module engine.math;

export namespace math {
    struct Vector3 { float x, y, z; };
    Vector3 cross_product(const Vector3& a, const Vector3& b);
}
```

### 1.4 Deducing `this` (C++23)
C++23 introduces explicitly deduced `this`, which can drastically reduce boilerplate when implementing `const` and non-`const` accessors, or implementing CRTP (Curiously Recurring Template Pattern).

```cpp
struct TransformComponent {
    Matrix4x4 matrix;

    template<typename Self>
    auto&& get_matrix(this Self&& self) {
        return std::forward<Self>(self).matrix;
    }
};
```

### 1.5 `std::expected` (C++23)
Exceptions are generally disabled in game engines due to unpredictable performance overhead. `std::expected` provides a type-safe way to return either a value or an error, forcing error handling without exceptions.

```cpp
std::expected<TextureHandle, ErrorCode> load_texture(std::string_view path) {
    if (!file_exists(path)) return std::unexpected(ErrorCode::FileNotFound);
    // Load...
    return handle;
}
```

## 2. Custom Memory Allocators

Dynamic allocations using general-purpose `new` or `malloc` are too slow and cause fragmentation. Engines pre-allocate large blocks of memory and manage it explicitly.

### 2.1 Linear / Arena Allocator
The simplest and fastest allocator. Memory is allocated by advancing a pointer. Deallocation is only possible for the entire arena at once. Perfect for per-frame temporary allocations (Frame Allocators).

```cpp
class LinearAllocator {
    void* start;
    size_t offset;
    size_t capacity;
public:
    void* allocate(size_t size, size_t alignment) {
        // align offset...
        void* ptr = (char*)start + offset;
        offset += size;
        return ptr;
    }
    void reset() { offset = 0; }
};
```

### 2.2 Pool Allocator
Allocates blocks of exactly the same size. Extremely fast and suffers from zero external fragmentation. Perfect for systems where many objects of the same type are created and destroyed (e.g., Particles, ECS Components).

### 2.3 Polymorphic Memory Resources (PMR - C++17)
The `<memory_resource>` header allows changing allocators at runtime without changing the type of the container. 

```cpp
std::pmr::monotonic_buffer_resource frame_arena{frame_buffer, frame_buffer_size};
std::pmr::vector<GameObject*> frame_objects{&frame_arena};
```

## 3. Entity-Component-Systems (ECS)

Traditional Deep Inheritance (e.g., `Entity -> MovableEntity -> Player`) suffers from the "diamond problem", poor cache coherency, and inflexible designs.

ECS relies on **Data-Oriented Design (DOD)**:
- **Entity**: Just a unique integer ID.
- **Component**: Pure Plain Old Data (POD) struct (no logic).
- **System**: Logic that iterates over all Entities possessing a specific set of Components.

### 3.1 Sparse Sets vs Archetypes
There are two main ways to store components in an ECS to ensure contiguous memory access:

1. **Sparse Sets (e.g., EnTT)**:
   - Each component type has its own dense array and a sparse array mapping Entity IDs to dense array indices.
   - Fast to add/remove components.
   - Iterating requires checking multiple arrays for overlaps unless grouped.

2. **Archetypes (e.g., Flecs, Unity DOTS)**:
   - Entities with the exact same combination of components (an Archetype) are stored together in contiguous chunks.
   - Iterating over queries is blazing fast (perfect cache coherency).
   - Adding/removing components causes structural changes (moving data between chunks).

### 3.2 Cache Coherency
Modern CPUs are fast, but memory is slow. ECS ensures that when a System processes components, it reads them sequentially from memory, maximizing CPU cache line utilization and avoiding cache misses.

```cpp
// A typical system iterating over Position and Velocity
void physics_system(Registry& registry, float dt) {
    auto view = registry.view<Position, Velocity>();
    for (auto entity : view) {
        auto& pos = view.get<Position>(entity);
        auto& vel = view.get<Velocity>(entity);
        pos.value += vel.value * dt;
    }
}
```

## 4. Cross-Platform Graphics API Abstractions (Vulkan/DirectX12)

Modern explicit APIs (Vulkan, DX12, Metal) provide low-level access to the GPU, requiring the engine to manage synchronization, memory, and pipeline states explicitly.

### 4.1 Frame Graph / Render Graph
Instead of executing rendering commands immediately, modern engines record render passes into a Directed Acyclic Graph (DAG) during the frame.
- **Benefits**: Automatic resource barrier generation, optimal transient memory aliasing, and render pass reordering/culling.

### 4.2 Bindless Architecture
Instead of binding textures and buffers per-draw call (which is CPU intensive), Bindless relies on uploading all resources into massive descriptor arrays.
- The GPU indexes into these arrays using indices passed via push constants or instance data.
- Drastically reduces CPU overhead and allows consolidating multiple draw calls into a single indirect draw.

### 4.3 Shader Translation and Abstraction
Writing shaders in GLSL/HLSL for every platform is unmanageable.
- **Slang**: A modern shader language that compiles to SPIR-V (Vulkan), DXIL (DX12), and MSL (Metal).
- SPIR-V cross-compilation (using SPIRV-Cross) is also widely used.

### 4.4 Command Buffers and Multithreading
Explicit APIs allow command buffers to be recorded on multiple CPU threads simultaneously without locking.
- Divide the scene into chunks.
- Assign each chunk to a thread in the thread pool.
- Each thread records secondary command buffers.
- The main thread submits them sequentially to the GPU queue.

## Conclusion
Building a modern C++ engine requires unlearning old object-oriented habits and embracing Data-Oriented Design. By combining C++20/23 features for safety and expressiveness with explicit memory control, ECS, and modern graphics pipelines, you can build an engine capable of fully utilizing next-generation hardware.

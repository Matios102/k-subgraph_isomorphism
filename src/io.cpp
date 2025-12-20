#include "io.h"
#include <fstream>
#include <stdexcept>
#include <sstream>
#include <iostream>
#include <chrono>
#include <thread>

#ifndef _WIN32
#include <unistd.h>
#endif

#ifdef _WIN32
#include <windows.h>
#endif

static Graph read_single_graph(std::ifstream &in)
{
    Graph G;

    std::string line;

    while (std::getline(in, line))
    {
        if (!line.empty())
            break;
    }
    if (line.empty())
        throw std::runtime_error("Unexpected end of file while reading vertex count.");

    std::istringstream iss(line);
    if (!(iss >> G.n) || G.n <= 0)
        throw std::runtime_error("Invalid vertex count in input.");

    G.A.assign(G.n, std::vector<int>(G.n, 0));

    for (int i = 0; i < G.n; ++i)
    {
        if (!std::getline(in, line))
            throw std::runtime_error("Not enough rows for adjacency matrix.");

        std::istringstream row(line);
        for (int j = 0; j < G.n; ++j)
        {
            if (!(row >> G.A[i][j]))
                throw std::runtime_error("Malformed adjacency matrix row.");
        }
    }

    return G;
}

std::pair<Graph, Graph> read_input_file(const std::string &path)
{
    std::ifstream in(path);
    if (!in.is_open())
    {
        throw std::runtime_error("Cannot open input file: " + path);
    }

    Graph G1 = read_single_graph(in);
    Graph G2 = read_single_graph(in);

    return {G1, G2};
}

#ifdef _WIN32
static bool enable_virtual_terminal_colors()
{
    HANDLE handle = GetStdHandle(STD_OUTPUT_HANDLE);
    if (handle == INVALID_HANDLE_VALUE)
    {
        return false;
    }

    DWORD mode = 0;
    if (!GetConsoleMode(handle, &mode))
    {
        return false;
    }

    if (mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    {
        return true;
    }

    return SetConsoleMode(handle, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
}
#endif

void print_result(const Graph &G,
                  const Graph &H,
                  const Matrix &extension,
                  std::ostream &out,
                  bool enableColor)
{
    if (static_cast<int>(extension.size()) != H.n)
    {
        throw std::runtime_error("Extension matrix dimensions must match graph H.");
    }
    for (const auto &row : extension)
    {
        if (static_cast<int>(row.size()) != H.n)
        {
            throw std::runtime_error("Extension matrix dimensions must match graph H.");
        }
    }

    Graph extendedH = H;
    long long cost = 0;

    for (int i = 0; i < H.n; ++i)
    {
        for (int j = 0; j < H.n; ++j)
        {
            extendedH.A[i][j] += extension[i][j];
            cost += extension[i][j];
        }
    }

    bool colorEnabled = enableColor && (&out == &std::cout);
#ifdef _WIN32
    if (colorEnabled)
    {
        colorEnabled = enable_virtual_terminal_colors();
    }
#else
    if (colorEnabled)
    {
        colorEnabled = ::isatty(::fileno(stdout));
    }
#endif

    const std::vector<std::string> palette = {
        "\x1b[31m", "\x1b[32m", "\x1b[33m", "\x1b[34m", "\x1b[35m", "\x1b[36m",
        "\x1b[91m", "\x1b[92m", "\x1b[93m", "\x1b[94m", "\x1b[95m", "\x1b[96m",
        "\x1b[41m\x1b[30m", "\x1b[42m\x1b[30m", "\x1b[43m\x1b[30m", "\x1b[44m\x1b[97m",
        "\x1b[45m\x1b[97m", "\x1b[46m\x1b[30m", "\x1b[100m\x1b[97m", "\x1b[104m\x1b[30m"};
    const std::string dimColor = "\x1b[90m";
    const std::string titleColor = "\x1b[95m";
    const std::string resetColor = "\x1b[0m";

    auto rainbow_line = [&](int width)
    {
        if (!colorEnabled)
        {
            for (int i = 0; i < width; ++i)
                out << "-";
            out << "\n";
            return;
        }
        const char symbols[] = {'#', '*', '+', '@', '%', '&'};
        for (int i = 0; i < width; ++i)
        {
            const std::string &c = palette[i % palette.size()];
            char sym = symbols[i % (sizeof(symbols) / sizeof(symbols[0]))];
            out << c << sym;
        }
        out << resetColor << "\n";
    };

    if (colorEnabled)
    {
        const char spinnerFrames[] = {'|', '/', '-', '\\'};
        for (int k = 0; k < 8; ++k)
        {
            char frame = spinnerFrames[k % 4];
            const std::string &c = palette[k % palette.size()];
            out << "\r" << c << "Color blast " << frame << resetColor;
            out.flush();
            std::this_thread::sleep_for(std::chrono::milliseconds(60));
        }
        out << "\r" << std::string(20, ' ') << "\r";
    }

    auto print_matrix_frame = [&](const Matrix &M, bool highlight, int offset)
    {
        int rows = static_cast<int>(M.size());
        int cols = rows > 0 ? static_cast<int>(M[0].size()) : 0;
        for (int i = 0; i < rows; ++i)
        {
            if (colorEnabled)
            {
                out << "\r\x1b[2K"; // clear line and carriage return
            }
            for (int j = 0; j < cols; ++j)
            {
                bool added = highlight && extension[i][j] > 0;
                if (colorEnabled)
                {
                    if (added)
                    {
                        const std::string &c = palette[(i * 7 + j * 5 + offset) % palette.size()];
                        out << c << M[i][j] << resetColor;
                    }
                    else
                    {
                        const std::string &c = palette[(i + j + 3 + offset) % palette.size()];
                        out << dimColor << c << M[i][j] << resetColor;
                    }
                }
                else
                {
                    out << M[i][j];
                }
                if (j + 1 < cols)
                {
                    out << ' ';
                }
            }
            out << "\n";
        }
    };

    auto print_block = [&](int offset)
    {
        rainbow_line(40);
        out << (colorEnabled ? titleColor : "") << "Input (G):" << (colorEnabled ? resetColor : "") << "\n";
        print_matrix_frame(G.A, false, offset);
        out << (colorEnabled ? titleColor : "") << "Input (H):" << (colorEnabled ? resetColor : "") << "\n";
        print_matrix_frame(H.A, false, offset + 2);
        rainbow_line(40);
        out << (colorEnabled ? titleColor : "") << "Extension of H (colored additions):" << (colorEnabled ? resetColor : "") << "\n";
        print_matrix_frame(extendedH.A, true, offset + 4);
        rainbow_line(40);
    };

    // Initial print
    print_block(0);

    if (colorEnabled)
    {
        int blockLines = 3                  // rainbow lines
                         + 3                // section titles
                         + G.n + H.n + H.n; // matrices
        const int frames = 100;
        for (int f = 0; f < frames; ++f)
        {
            int offset = f * 5;
            // Move cursor up to the start of the block
            out << "\x1b[" << blockLines << "A";
            print_block(offset);
            out.flush();
            if (f + 1 < frames)
            {
                std::this_thread::sleep_for(std::chrono::milliseconds(80));
            }
        }
    }

    out << "Metric: " << cost << "\n";
}

#include "exact.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>

static void EnumerateMappings_rec(
    int mappedCount,
    const Graph &G,
    const Graph &H,
    std::vector<int> &partial,
    std::vector<bool> &used,
    Matrix &allMappings)
{
    int nG = G.n;
    int nH = H.n;

    if (mappedCount == nG)
    {
        allMappings.push_back(partial);
        return;
    }

    int u = mappedCount;

    for (int v = 0; v < nH; ++v)
    {
        if (!used[v])
        {
            partial[u] = v;
            used[v] = true;
            EnumerateMappings_rec(mappedCount + 1, G, H, partial, used, allMappings);
            used[v] = false;
            partial[u] = -1;
        }
    }
}

static Matrix EnumerateMappings(const Graph &G, const Graph &H)
{
    Matrix allMappings;
    std::vector<int> partial(G.n, -1);
    std::vector<bool> used(H.n, false);

    EnumerateMappings_rec(0, G, H, partial, used, allMappings);
    return allMappings;
}

static void generateCombinations_rec(
    const Matrix &Mapping,
    int k,
    int start,
    std::vector<int> &current,
    Matrix &allComb)
{
    if (static_cast<int>(current.size()) == k)
    {
        allComb.push_back(current);
        return;
    }
    int m = static_cast<int>(Mapping.size());
    for (int i = start; i < m; ++i)
    {
        current.push_back(i);
        generateCombinations_rec(Mapping, k, i + 1, current, allComb);
        current.pop_back();
    }
}

static Matrix Combinations(const Matrix &Mapping, int k)
{
    Matrix allComb;
    if (k <= 0 || k > static_cast<int>(Mapping.size()))
    {
        return allComb;
    }
    std::vector<int> current;
    generateCombinations_rec(Mapping, k, 0, current, allComb);
    return allComb;
}

Matrix exact_minimal_k_extension(
    const Graph &G,
    const Graph &H,
    int k)
{
    const auto &A_G = G.A;
    const auto &A_H = H.A;

    Matrix Mapping;

    Mapping = EnumerateMappings(G, H);

    long long minCost = std::numeric_limits<long long>::max();

    int nH = H.n;
    Matrix minExtension(nH, std::vector<int>(nH, 0));

    auto allComb = Combinations(Mapping, k);
    for (const auto &combIndices : allComb)
    {
        Matrix requiredEdges(nH, std::vector<int>(nH, 0));

        for (int idx : combIndices)
        {
            const std::vector<int> &f = Mapping[idx];

            for (int u = 0; u < G.n; ++u)
            {
                for (int v = 0; v < G.n; ++v)
                {
                    if (A_G[u][v] > 0)
                    {
                        int x = f[u];
                        int y = f[v];
                        int delta = std::max(0, A_G[u][v] - A_H[x][y]);
                        requiredEdges[x][y] = std::max(requiredEdges[x][y], delta);
                    }
                }
            }
        }

        long long cost = 0;
        for (int x = 0; x < nH; ++x)
        {
            for (int y = 0; y < nH; ++y)
            {
                cost += requiredEdges[x][y];
            }
        }

        if (cost < minCost)
        {
            minCost = cost;
            minExtension = requiredEdges;
        }
    }

    return minExtension;
}

void run_exact_algorithm(const std::string &inputPath,
                         const std::optional<std::string> &outputPath,
                         int k)
{
    auto [G, H] = read_input_file(inputPath);

    if (k <= 0)
    {
        throw std::runtime_error("k must be positive.");
    }

    auto minExtension = exact_minimal_k_extension(G, H, k);

    std::ostream *out = &std::cout;
    std::ofstream fileOut;
    if (outputPath.has_value())
    {
        fileOut.open(*outputPath);
        if (!fileOut.is_open())
        {
            throw std::runtime_error("Cannot open output file: " + *outputPath);
        }
        out = &fileOut;
    }

    for (int i = 0; i < H.n; ++i)
    {
        for (int j = 0; j < H.n; ++j)
        {
            (*out) << minExtension[i][j] + H.A[i][j];
            if (j + 1 < H.n)
                (*out) << " ";
        }
        (*out) << "\n";
    }
}

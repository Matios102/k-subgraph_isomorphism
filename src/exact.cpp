#include "exact.h"

#include <algorithm>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

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


static void generateMultiComb_rec(
    int m,          // number of mappings
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
    for (int i = start; i < m; ++i)
    {
        current.push_back(i);
        // i (not i+1) allows repetition
        generateMultiComb_rec(m, k, i, current, allComb);
        current.pop_back();
    }
}

static Matrix MultiCombinationsWithRepetition(int numMappings, int k)
{
    Matrix allComb;
    if (k <= 0 || numMappings <= 0)
    {
        return allComb;
    }

    std::vector<int> current;
    generateMultiComb_rec(numMappings, k, 0, current, allComb);
    return allComb;
}


Matrix exact_minimal_k_extension(
    const Graph &G,
    const Graph &H,
    int k)
{
    const auto &A_G = G.A;
    const auto &A_H = H.A;

    Matrix Mapping = EnumerateMappings(G, H);
    int numMappings = static_cast<int>(Mapping.size());

    if (numMappings == 0)
    {
        throw std::runtime_error("No valid mappings from G to H exist.");
    }

    // All k-multicombinations with repetition of mapping indices
    Matrix allComb = MultiCombinationsWithRepetition(numMappings, k);

    long long minCost = std::numeric_limits<long long>::max();
    int nH = H.n;
    Matrix minExtension(nH, std::vector<int>(nH, 0));

    for (const auto &combIndices : allComb)
    {
        // multiplicity of each mapping i in this multiset
        std::vector<int> mult(numMappings, 0);
        for (int idx : combIndices)
        {
            ++mult[idx];
        }

        Matrix demandMax(nH, std::vector<int>(nH, 0));

        for (int i = 0; i < numMappings; ++i)
        {
            int mi = mult[i];
            if (mi == 0)
                continue;

            const std::vector<int> &f = Mapping[i];

            Matrix demand_i(nH, std::vector<int>(nH, 0));

            for (int u = 0; u < G.n; ++u)
            {
                for (int v = 0; v < G.n; ++v)
                {
                    if (A_G[u][v] > 0)
                    {
                        int x = f[u];
                        int y = f[v];
                        demand_i[x][y] += A_G[u][v];
                    }
                }
            }

            for (int x = 0; x < nH; ++x)
            {
                for (int y = 0; y < nH; ++y)
                {
                    if (demand_i[x][y] > 0)
                    {
                        int totalDemand = mi * demand_i[x][y];
                        if (totalDemand > demandMax[x][y])
                        {
                            demandMax[x][y] = totalDemand;
                        }
                    }
                }
            }
        }

        // Now compute required extension for this multiset of embeddings
        Matrix requiredEdges(nH, std::vector<int>(nH, 0));
        long long cost = 0;

        for (int x = 0; x < nH; ++x)
        {
            for (int y = 0; y < nH; ++y)
            {
                int needed = std::max(0, demandMax[x][y] - A_H[x][y]);
                requiredEdges[x][y] = needed;
                cost += needed;
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
    if (k <= 0)
    {
        throw std::runtime_error("k must be positive.");
    }

    auto [G, H] = read_input_file(inputPath);

    if (G.n > H.n)
    {
        throw std::runtime_error("Graph G must not have more vertices than H.");
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

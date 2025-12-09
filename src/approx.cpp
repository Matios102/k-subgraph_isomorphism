#include "approx.h"
#include "io.h"

#include <vector>
#include <limits>
#include <stdexcept>
#include <fstream>
#include <iostream>
#include <cmath>

using CostType = long long;
static constexpr CostType INF_COST =
    std::numeric_limits<CostType>::max() / 4;

static std::pair<int, int> DegreeSignature(const std::vector<std::vector<int>> &A,
                                           int v)
{
    int n = static_cast<int>(A.size());
    int outDeg = 0;
    int inDeg = 0;

    // out-degree: sum_j A[v][j]
    for (int j = 0; j < n; ++j)
    {
        outDeg += A[v][j];
    }
    // in-degree: sum_i A[i][v]
    for (int i = 0; i < n; ++i)
    {
        inDeg += A[i][v];
    }

    return {outDeg, inDeg};
}

static std::vector<int> hungarian_min_cost_injective_assignment(
    const std::vector<std::vector<CostType>> &C)
{
    int n = static_cast<int>(C.size());
    if (n == 0)
    {
        return {};
    }
    int m = static_cast<int>(C[0].size());
    if (m < n)
    {
        throw std::runtime_error("Hungarian algorithm requires n <= m.");
    }

    std::vector<CostType> uLabels(n, 0);

    std::vector<CostType> vLabels(m, INF_COST);
    for (int v = 0; v < m; ++v)
    {
        CostType mn = INF_COST;
        for (int u = 0; u < n; ++u)
        {
            if (C[u][v] < mn)
            {
                mn = C[u][v];
            }
        }
        vLabels[v] = mn;
    }

    std::vector<int> f(n, -1);
    std::vector<int> f_inv(m, -1);

    for (int u0 = 0; u0 < n; ++u0)
    {
        if (f[u0] != -1)
        {
            // already matched via earlier augmentation
            continue;
        }

        std::vector<CostType> minSlack(m, INF_COST);
        std::vector<int> prev(m, -1);

        std::vector<bool> S(n, false);
        std::vector<bool> T(m, false);

        S[u0] = true;

        std::vector<int> parent(n, -1);
        std::vector<int> queue;
        queue.push_back(u0);
        int qHead = 0;

        while (f[u0] == -1)
        {
            if (qHead >= static_cast<int>(queue.size()))
            {
                // If queue is empty, we still need to adjust labels using minSlack.
            }
            else
            {
                while (qHead < static_cast<int>(queue.size()))
                {
                    int u = queue[qHead++];
                    for (int v = 0; v < m; ++v)
                    {
                        if (T[v])
                            continue;

                        CostType delta = C[u][v] - uLabels[u] - vLabels[v];
                        if (delta < minSlack[v])
                        {
                            minSlack[v] = delta;
                            prev[v] = u;
                        }
                    }
                }
            }

            int v_star = -1;
            CostType Delta = INF_COST;
            for (int v = 0; v < m; ++v)
            {
                if (!T[v] && minSlack[v] < Delta)
                {
                    Delta = minSlack[v];
                    v_star = v;
                }
            }
            if (v_star == -1)
            {
                throw std::runtime_error("Hungarian algorithm failed: no augmenting path.");
            }

            for (int u = 0; u < n; ++u)
            {
                if (S[u])
                {
                    uLabels[u] += Delta;
                }
            }
            for (int v = 0; v < m; ++v)
            {
                if (T[v])
                {
                    vLabels[v] -= Delta;
                }
            }
            for (int v = 0; v < m; ++v)
            {
                if (!T[v])
                {
                    minSlack[v] -= Delta;
                }
            }

            T[v_star] = true;

            if (f_inv[v_star] == -1)
            {
                int v = v_star;
                while (v != -1)
                {
                    int u = prev[v];
                    int next_v = f[u];
                    f[u] = v;
                    f_inv[v] = u;
                    v = next_v;
                }
            }
            else
            {
                int u2 = f_inv[v_star];
                if (!S[u2])
                {
                    S[u2] = true;
                    queue.push_back(u2);
                    parent[u2] = v_star;
                }
            }
        }
    }

    return f;
}

Graph approx_k_extension(const Graph &G,
                         const Graph &H,
                         int k)
{
    if (k <= 0)
    {
        throw std::runtime_error("k must be positive in approximation algorithm.");
    }
    if (G.n > H.n)
    {
        throw std::runtime_error("Graph G must not have more vertices than H.");
    }

    const auto &A_G = G.A;
    Graph H_mod = H;
    auto &A_H = H_mod.A;

    int nG = G.n;
    int nH = H.n;

    // Store all previously found embeddings
    std::vector<std::vector<int>> Embeddings;

    // Soft reuse-count for (u,v) pairs: how many times we mapped u -> v
    std::vector<std::vector<int>> UsedCount(nG, std::vector<int>(nH, 0));

    // Penalty factor for reusing the same (u, v)
    // Just needs to be "big enough" relative to degree differences.
    const CostType REUSE_PENALTY = 1000;

    for (int iter = 1; iter <= k; ++iter)
    {
        // 1. Degree signatures
        std::vector<std::pair<int, int>> sigG(nG);
        std::vector<std::pair<int, int>> sigH(nH);

        for (int u = 0; u < nG; ++u)
        {
            sigG[u] = DegreeSignature(A_G, u);
        }
        for (int v = 0; v < nH; ++v)
        {
            sigH[v] = DegreeSignature(A_H, v);
        }

        // 2. Cost matrix: degree-diff + soft penalty for reusing (u,v)
        std::vector<std::vector<CostType>> C(nG, std::vector<CostType>(nH, 0));

        for (int u = 0; u < nG; ++u)
        {
            for (int v = 0; v < nH; ++v)
            {
                int d_out_G = sigG[u].first;
                int d_in_G = sigG[u].second;

                int d_out_H = sigH[v].first;
                int d_in_H = sigH[v].second;

                CostType degCost =
                    static_cast<CostType>(std::llabs(static_cast<long long>(d_out_G - d_out_H))) +
                    static_cast<CostType>(std::llabs(static_cast<long long>(d_in_G - d_in_H)));

                CostType penalty =
                    static_cast<CostType>(UsedCount[u][v]) * REUSE_PENALTY;

                CostType val = degCost + penalty;
                if (val > INF_COST)
                    val = INF_COST;
                C[u][v] = val;
            }
        }

        // 3. Get an embedding from Hungarian
        std::vector<int> f = hungarian_min_cost_injective_assignment(C);

        // 4. Standard delta-update so that this embedding is realizable
        for (int u = 0; u < nG; ++u)
        {
            for (int v = 0; v < nG; ++v)
            {
                if (A_G[u][v] > 0)
                {
                    int x = f[u];
                    int y = f[v];

                    // Need at least A_G[u][v] edges in H_mod[x][y]
                    int delta = std::max(0, A_G[u][v] - A_H[x][y]);
                    A_H[x][y] += delta;
                }
            }
        }

        // 5. Check how many times this exact mapping appeared before
        int sameCount = 0;
        for (const auto &prev : Embeddings)
        {
            if (prev == f)
            {
                ++sameCount;
            }
        }

        // If this mapping already appeared `sameCount` times,
        // ensure enough multiplicity so sameCount+1 "copies" can be distinguished
        if (sameCount > 0)
        {
            for (int u = 0; u < nG; ++u)
            {
                for (int v = 0; v < nG; ++v)
                {
                    if (A_G[u][v] > 0)
                    {
                        int x = f[u];
                        int y = f[v];

                        // Required multiplicity for this edge in H:
                        // (sameCount + 1) copies of the G-edge.
                        int required = (sameCount + 1) * A_G[u][v];
                        if (A_H[x][y] < required)
                        {
                            int extra = required - A_H[x][y];
                            A_H[x][y] += extra;
                        }
                    }
                }
            }
        }

        // 6. Update reuse counts and store this embedding
        for (int u = 0; u < nG; ++u)
        {
            int v = f[u];
            if (v >= 0 && v < nH)
            {
                UsedCount[u][v] += 1;
            }
        }

        Embeddings.push_back(f);
    }

    return H_mod;
}

void run_approx_algorithm(const std::string &inputPath,
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

    Graph extension = approx_k_extension(G, H, k);

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
            (*out) << extension.A[i][j];
            if (j + 1 < H.n)
                (*out) << " ";
        }
        (*out) << "\n";
    }
}

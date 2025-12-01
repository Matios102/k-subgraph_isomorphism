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
                // This situation is handled by directly proceeding to choosing v*.
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

    std::vector<std::vector<bool>> UsedPairs(nG, std::vector<bool>(nH, false));

    std::vector<std::vector<int>> Embeddings;

    for (int iter = 1; iter <= k; ++iter)
    {
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

        std::vector<std::vector<CostType>> C(nG, std::vector<CostType>(nH, 0));

        for (int u = 0; u < nG; ++u)
        {
            for (int v = 0; v < nH; ++v)
            {
                int d_out_G = sigG[u].first;
                int d_in_G = sigG[u].second;

                int d_out_H = sigH[v].first;
                int d_in_H = sigH[v].second;

                CostType val =
                    static_cast<CostType>(std::llabs(static_cast<long long>(d_out_G - d_out_H))) +
                    static_cast<CostType>(std::llabs(static_cast<long long>(d_in_G - d_in_H)));

                if (UsedPairs[u][v])
                {
                    C[u][v] = INF_COST;
                }
                else
                {
                    C[u][v] = val;
                }
            }
        }

        std::vector<int> f = hungarian_min_cost_injective_assignment(C);

        for (int u = 0; u < nG; ++u)
        {
            for (int v = 0; v < nG; ++v)
            {
                if (A_G[u][v] > 0)
                {
                    int x = f[u];
                    int y = f[v];

                    A_H[x][y] += A_G[u][v];
                }
            }
        }

        for (int u = 0; u < nG; ++u)
        {
            int v = f[u];
            if (v >= 0 && v < nH)
            {
                UsedPairs[u][v] = true;
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
    auto [G, H] = read_input_file(inputPath);

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

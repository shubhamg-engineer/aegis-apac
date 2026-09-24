"""Hydraulic Inundation & Overland Attenuation Engine.

Computes coastal surge inundation depth across Digital Surface Model (DSM)
terrain, enforcing calibrated inland attenuation decay and strict 8-connected
hydraulic connectivity to the marine boundary.
"""

from collections import deque
from typing import Dict, Tuple
import numpy as np


class HydraulicInundation:
    """Calculates overland surge inundation with hydraulic connectivity filtering."""

    def __init__(self, inland_attenuation_decay: float = 0.00018):
        # Default decay rate: 0.18 m drop per kilometer inland (0.00018 m/m)
        self.decay_per_m = inland_attenuation_decay

    def compute_distance_to_coast(self, sea_mask: np.ndarray, cell_size_m: float = 500.0) -> np.ndarray:
        """Compute Euclidean distance in meters from each land cell to the nearest sea cell."""
        ny, nx = sea_mask.shape
        dist = np.full((ny, nx), np.inf, dtype=float)
        queue = deque()

        # Initialize all sea cells with distance 0
        for y in range(ny):
            for x in range(nx):
                if sea_mask[y, x] == 1:
                    dist[y, x] = 0.0
                    queue.append((y, x))

        # BFS expansion for Euclidean distance approximation
        while queue:
            cy, cx = queue.popleft()
            current_dist = dist[cy, cx]

            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                ny_coord, nx_coord = cy + dy, cx + dx
                if 0 <= ny_coord < ny and 0 <= nx_coord < nx:
                    step_cost = cell_size_m * (1.414 if dy != 0 and dx != 0 else 1.0)
                    new_dist = current_dist + step_cost
                    if new_dist < dist[ny_coord, nx_coord]:
                        dist[ny_coord, nx_coord] = new_dist
                        queue.append((ny_coord, nx_coord))

        return dist

    def compute_inundation(
        self,
        coastal_water_level_m: np.ndarray,
        elevation_m: np.ndarray,
        sea_mask: np.ndarray,
        inland_decay_rate: float = None,
        cell_size_m: float = 500.0,
    ) -> Dict[str, np.ndarray]:
        """Compute effective attenuated water level and hydraulically connected surge depths."""
        decay = inland_decay_rate if inland_decay_rate is not None else self.decay_per_m
        dist_to_coast_m = self.compute_distance_to_coast(sea_mask, cell_size_m)
        
        # 1. Effective attenuated water level
        effective_water_level = np.maximum(
            0.0,
            coastal_water_level_m - (decay * dist_to_coast_m)
        )
        
        # Candidate flooded cells: land cells where effective water level exceeds ground elevation
        candidate_flood = (effective_water_level > elevation_m) & (sea_mask == 0)
        
        # 2. Hydraulic Connectivity Filtering (BFS flood-fill from marine boundary)
        ny, nx = elevation_m.shape
        connected_flood_mask = np.zeros((ny, nx), dtype=bool)
        queue = deque()
        
        # Start flood fill from sea boundary cells that border land
        for y in range(ny):
            for x in range(nx):
                if sea_mask[y, x] == 1:
                    # Check if neighboring a candidate flooded cell
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny_coord, nx_coord = y + dy, x + dx
                        if 0 <= ny_coord < ny and 0 <= nx_coord < nx:
                            if candidate_flood[ny_coord, nx_coord] and not connected_flood_mask[ny_coord, nx_coord]:
                                connected_flood_mask[ny_coord, nx_coord] = True
                                queue.append((ny_coord, nx_coord))

        while queue:
            cy, cx = queue.popleft()
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                ny_coord, nx_coord = cy + dy, cx + dx
                if 0 <= ny_coord < ny and 0 <= nx_coord < nx:
                    if candidate_flood[ny_coord, nx_coord] and not connected_flood_mask[ny_coord, nx_coord]:
                        connected_flood_mask[ny_coord, nx_coord] = True
                        queue.append((ny_coord, nx_coord))

        # 3. Calculate surge depth: only where hydraulically connected
        surge_depth = np.zeros_like(elevation_m, dtype=float)
        surge_depth[connected_flood_mask] = effective_water_level[connected_flood_mask] - elevation_m[connected_flood_mask]
        surge_depth = np.maximum(0.0, surge_depth)

        return {
            "effective_water_level_m": effective_water_level,
            "dist_to_coast_m": dist_to_coast_m,
            "connected_flood_mask": connected_flood_mask,
            "surge_depth_m": surge_depth,
        }

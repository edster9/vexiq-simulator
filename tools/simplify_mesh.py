#!/usr/bin/env python3
"""
Mesh Simplification Tool
========================
Reduces polygon count on OBJ files using quadric decimation.

Usage:
    python3 simplify_mesh.py input.obj output.obj [target_faces]
    python3 simplify_mesh.py input.obj output.obj 0.9  # 90% reduction
"""

import sys
import os
import trimesh
import fast_simplification


def simplify_mesh(input_path: str, output_path: str, target: float = 0.9) -> bool:
    """Simplify a mesh by reducing polygon count.

    Args:
        input_path: Path to input OBJ file
        output_path: Path for output OBJ file
        target: If < 1, reduction ratio (0.9 = remove 90% of faces)
                If >= 1, target face count

    Returns:
        True if successful
    """
    try:
        mesh = trimesh.load(input_path)
        original_faces = len(mesh.faces)
        original_verts = len(mesh.vertices)

        print(f"Loading: {input_path}")
        print(f"  Original: {original_verts:,} verts, {original_faces:,} faces")

        # Determine reduction
        if target < 1:
            reduction = target
            target_faces = int(original_faces * (1 - reduction))
        else:
            target_faces = int(target)
            reduction = 1 - (target_faces / original_faces)

        print(f"  Target: {target_faces:,} faces ({reduction*100:.0f}% reduction)")

        # Simplify
        verts_out, faces_out = fast_simplification.simplify(
            mesh.vertices,
            mesh.faces,
            target_reduction=reduction
        )

        print(f"  Result: {len(verts_out):,} verts, {len(faces_out):,} faces")

        # Create and save simplified mesh
        simplified = trimesh.Trimesh(vertices=verts_out, faces=faces_out)
        simplified.export(output_path)

        size = os.path.getsize(output_path)
        print(f"  Saved: {output_path} ({size/1024:.0f} KB)")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def batch_simplify(models_dir: str, target_faces: int = 5000):
    """Simplify all high-poly models in a directory.

    Models with more than target_faces*2 will be simplified.
    """
    threshold = target_faces * 2  # Only simplify if more than 2x target

    for filename in os.listdir(models_dir):
        if not filename.endswith('.obj') or '_lowpoly' in filename:
            continue

        filepath = os.path.join(models_dir, filename)

        # Check face count
        mesh = trimesh.load(filepath)
        if len(mesh.faces) <= threshold:
            print(f"Skipping {filename}: {len(mesh.faces):,} faces (under threshold)")
            continue

        # Create lowpoly version
        output_path = filepath.replace('.obj', '_lowpoly.obj')
        reduction = 1 - (target_faces / len(mesh.faces))
        simplify_mesh(filepath, output_path, reduction)
        print()


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 simplify_mesh.py input.obj output.obj [reduction]")
        print("       python3 simplify_mesh.py --batch models_dir/ [target_faces]")
        print("\nExamples:")
        print("  simplify_mesh.py model.obj model_low.obj 0.9    # 90% reduction")
        print("  simplify_mesh.py model.obj model_low.obj 5000   # Target 5000 faces")
        print("  simplify_mesh.py --batch models/parts/ 3000     # Batch with 3000 target")
        sys.exit(1)

    if sys.argv[1] == '--batch':
        models_dir = sys.argv[2]
        target = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
        batch_simplify(models_dir, target)
    else:
        input_path = sys.argv[1]
        output_path = sys.argv[2]
        target = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9
        simplify_mesh(input_path, output_path, target)


if __name__ == '__main__':
    main()

"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

/**
 * Animated 3D background: a slowly rotating wireframe globe surrounded by a
 * field of glowing "job" nodes — a nod to the global, remote nature of the
 * opportunities Work From Vacation surfaces. Rendered to a fixed, full-screen
 * canvas behind the app content. Pointer-events are disabled so it never
 * interferes with the UI, and it respects `prefers-reduced-motion`.
 */
export default function ThreeBackground() {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.z = 8;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
    mount.appendChild(renderer.domElement);

    const world = new THREE.Group();
    scene.add(world);

    // ── Wireframe globe ────────────────────────────────────────────────
    const globeGeo = new THREE.IcosahedronGeometry(2.6, 2);
    const globe = new THREE.LineSegments(
      new THREE.WireframeGeometry(globeGeo),
      new THREE.LineBasicMaterial({
        color: 0x4f9dde,
        transparent: true,
        opacity: 0.16,
      })
    );
    world.add(globe);

    // Inner solid core for subtle depth.
    const core = new THREE.Mesh(
      new THREE.IcosahedronGeometry(2.55, 2),
      new THREE.MeshBasicMaterial({
        color: 0x121620,
        transparent: true,
        opacity: 0.55,
      })
    );
    world.add(core);

    // ── Orbiting "job" nodes (points on a shell) ───────────────────────
    const NODE_COUNT = 900;
    const positions = new Float32Array(NODE_COUNT * 3);
    const colors = new Float32Array(NODE_COUNT * 3);
    const blue = new THREE.Color(0x4f9dde);
    const green = new THREE.Color(0x46c08a);

    for (let i = 0; i < NODE_COUNT; i++) {
      // Even-ish distribution on a sphere via spherical coordinates.
      const r = 3.2 + Math.random() * 1.8;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = r * Math.cos(phi);

      const c = Math.random() > 0.5 ? blue : green;
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }

    const nodesGeo = new THREE.BufferGeometry();
    nodesGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    nodesGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const nodes = new THREE.Points(
      nodesGeo,
      new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        transparent: true,
        opacity: 0.85,
        sizeAttenuation: true,
      })
    );
    world.add(nodes);

    // Distant faint starfield for depth.
    const STAR_COUNT = 400;
    const starPos = new Float32Array(STAR_COUNT * 3);
    for (let i = 0; i < STAR_COUNT; i++) {
      starPos[i * 3] = (Math.random() - 0.5) * 40;
      starPos[i * 3 + 1] = (Math.random() - 0.5) * 40;
      starPos[i * 3 + 2] = (Math.random() - 0.5) * 40;
    }
    const starsGeo = new THREE.BufferGeometry();
    starsGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
    const stars = new THREE.Points(
      starsGeo,
      new THREE.PointsMaterial({
        color: 0x6b7686,
        size: 0.04,
        transparent: true,
        opacity: 0.5,
      })
    );
    scene.add(stars);

    world.rotation.x = 0.35;

    // ── Pointer parallax ───────────────────────────────────────────────
    const pointer = { x: 0, y: 0 };
    const onPointerMove = (e: PointerEvent) => {
      pointer.x = (e.clientX / window.innerWidth - 0.5) * 2;
      pointer.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("pointermove", onPointerMove);

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", onResize);

    // ── Animation loop ─────────────────────────────────────────────────
    let frame = 0;
    const clock = new THREE.Clock();

    const animate = () => {
      const t = clock.getElapsedTime();
      world.rotation.y = t * 0.08;
      nodes.rotation.y = -t * 0.04;
      stars.rotation.y = t * 0.01;

      // Ease camera toward the pointer for a parallax feel.
      camera.position.x += (pointer.x * 1.2 - camera.position.x) * 0.03;
      camera.position.y += (-pointer.y * 0.8 - camera.position.y) * 0.03;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
      if (!reduceMotion) frame = requestAnimationFrame(animate);
    };

    animate();
    if (reduceMotion) renderer.render(scene, camera); // single static frame

    // ── Cleanup ────────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      globeGeo.dispose();
      nodesGeo.dispose();
      starsGeo.dispose();
      (globe.material as THREE.Material).dispose();
      globe.geometry.dispose();
      (core.material as THREE.Material).dispose();
      core.geometry.dispose();
      (nodes.material as THREE.Material).dispose();
      (stars.material as THREE.Material).dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return <div ref={mountRef} className="three-bg" aria-hidden="true" />;
}

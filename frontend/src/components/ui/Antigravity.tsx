/* eslint-disable react/no-unknown-property */
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

interface AntigravityProps {
  count?: number;
  magnetRadius?: number;
  ringRadius?: number;
  waveSpeed?: number;
  waveAmplitude?: number;
  particleSize?: number;
  lerpSpeed?: number;
  color?: string;
  autoAnimate?: boolean;
  particleVariance?: number;
  rotationSpeed?: number;
  depthFactor?: number;
  pulseSpeed?: number;
  particleShape?: 'capsule' | 'sphere' | 'box' | 'tetrahedron';
  fieldStrength?: number;
  globalMouse?: { x: number; y: number };
}

const AntigravityInner = ({
  count = 300,
  magnetRadius = 10,
  ringRadius = 10,
  waveSpeed = 0.4,
  waveAmplitude = 1,
  particleSize = 2,
  lerpSpeed = 0.1,
  color = '#000000',
  particleVariance = 1,
  rotationSpeed = 0,
  depthFactor = 1,
  pulseSpeed = 3,
  particleShape = 'capsule',
  globalMouse
}: AntigravityProps) => {
  const meshRef = useRef<THREE.InstancedMesh>(null!);
  const { viewport } = useThree();
  const dummy = useMemo(() => new THREE.Object3D(), []);

  const virtualMouse = useRef({ x: 0, y: 0 });

  const particles = useMemo(() => {
    const temp = [];
    const width = (viewport.width || 100) * 1.5;
    const height = (viewport.height || 100) * 1.5;

    for (let i = 0; i < count; i++) {
      const t = Math.random() * 100;
      const speed = 0.01 + Math.random() / 200;
      
      const x = (Math.random() - 0.5) * width;
      const y = (Math.random() - 0.5) * height;
      const z = (Math.random() - 0.5) * 40;

      temp.push({
        t,
        speed,
        mx: x,
        my: y,
        mz: z,
        cx: x,
        cy: y,
        cz: z
      });
    }
    return temp;
  }, [count, viewport.width, viewport.height]);

  useFrame(state => {
    const mesh = meshRef.current;
    if (!mesh) return;

    const { viewport: v, pointer: m } = state;

    // Use globalMouse if available (overcomes pointer-events: none)
    const activeMouse = globalMouse || m;

    let destX = (activeMouse.x * v.width) / 2;
    let destY = (activeMouse.y * v.height) / 2;

    const smoothFactor = 0.05;
    virtualMouse.current.x += (destX - virtualMouse.current.x) * smoothFactor;
    virtualMouse.current.y += (destY - virtualMouse.current.y) * smoothFactor;

    const targetX = virtualMouse.current.x;
    const targetY = virtualMouse.current.y;

    particles.forEach((particle, i) => {
      let { t, speed, mx, my, mz } = particle;
      t = particle.t += speed / 2;

      const dx = mx - targetX;
      const dy = my - targetY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      let targetPos = { x: mx, y: my, z: mz * depthFactor };

      if (dist < magnetRadius) {
        const angle = Math.atan2(dy, dx);
        const currentRingRadius = ringRadius + Math.sin(t * waveSpeed) * waveAmplitude;
        
        targetPos.x = targetX + currentRingRadius * Math.cos(angle);
        targetPos.y = targetY + currentRingRadius * Math.sin(angle);
      }

      particle.cx += (targetPos.x - particle.cx) * lerpSpeed;
      particle.cy += (targetPos.y - particle.cy) * lerpSpeed;
      particle.cz += (targetPos.z - particle.cz) * lerpSpeed;

      dummy.position.set(particle.cx, particle.cy, particle.cz);
      dummy.lookAt(targetX, targetY, particle.cz);
      dummy.rotateX(Math.PI / 2);

      const baseScale = 0.6 + Math.sin(t * pulseSpeed) * 0.1 * particleVariance;
      const interactionScale = dist < magnetRadius ? 1.5 : 1;
      const finalScale = baseScale * interactionScale * particleSize;
      
      dummy.scale.set(finalScale, finalScale, finalScale);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
    });

    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[null as any, null as any, count]}>
      {particleShape === 'capsule' && <capsuleGeometry args={[0.1, 0.4, 4, 8]} />}
      {particleShape === 'sphere' && <sphereGeometry args={[0.2, 16, 16]} />}
      {particleShape === 'box' && <boxGeometry args={[0.3, 0.3, 0.3]} />}
      {particleShape === 'tetrahedron' && <tetrahedronGeometry args={[0.3]} />}
      <meshBasicMaterial color={color} />
    </instancedMesh>
  );
};

const Antigravity = (props: AntigravityProps) => {
  return (
    <Canvas camera={{ position: [0, 0, 50], fov: 35 }} style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: -1 }}>
      <AntigravityInner {...props} />
    </Canvas>
  );
};

export default Antigravity;

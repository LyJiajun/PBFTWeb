<template>
  <div class="canvas-container">
    <canvas ref="canvas" width="600" height="600"></canvas>
    <!-- 最终共识结果显示区域 -->
    <div class="consensus-result" v-if="finalConsensus">
      <h3>最终共识结果</h3>
      <p>{{ finalConsensus }}</p>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from "vue";

export default {
  props: ["topologyType", "nodeCount", "byzantineNodes", "simulationResult", "animationSpeed"],
  setup(props) {
    const canvas = ref(null);
    const ctx = ref(null);
    const nodeRadius = 20;
    const finalConsensus = ref("");
    const currentAnimationFrame = ref(null);  // 添加当前动画帧的引用

    // 使用 computed 缓存节点位置，只有 props.nodeCount 改变时才重新计算
    const nodePositions = computed(() => {
      const cx = 300,
        cy = 300,
        radius = 200;
      const positions = [];
      for (let i = 0; i < props.nodeCount; i++) {
        const angle = (i / props.nodeCount) * (2 * Math.PI);
        positions.push({
          x: cx + radius * Math.cos(angle),
          y: cy + radius * Math.sin(angle)
        });
      }
      return positions;
    });

    // 使用 computed 缓存节点颜色，只有 props.nodeCount 或 props.byzantineNodes 改变时才重新计算
    const nodeColors = computed(() => {
      const colors = Array(props.nodeCount).fill("green");
      for (let i = 0; i < props.byzantineNodes && i < props.nodeCount; i++) {
        colors[props.nodeCount - 1 - i] = "red";
      }
      return colors;
    });

    const drawNodes = () => {
      nodePositions.value.forEach((pos, i) => {
        ctx.value.beginPath();
        ctx.value.arc(pos.x, pos.y, nodeRadius, 0, Math.PI * 2);
        ctx.value.fillStyle = nodeColors.value[i];
        ctx.value.fill();
        ctx.value.stroke();
        ctx.value.fillStyle = "white";
        ctx.value.font = "14px Arial";
        ctx.value.fillText(i, pos.x - 5, pos.y + 5);
      });
    };

    const drawLine = (p1, p2) => {
      ctx.value.beginPath();
      ctx.value.moveTo(p1.x, p1.y);
      ctx.value.lineTo(p2.x, p2.y);
      ctx.value.strokeStyle = "#aaa";
      ctx.value.stroke();
    };

    // 绘制拓扑结构时直接使用缓存的节点位置和颜色，避免重复计算
    const drawTopology = () => {
      if (!ctx.value) return;
      ctx.value.clearRect(0, 0, 600, 600);
      const positions = nodePositions.value;

      if (props.topologyType === "full") {
        for (let i = 0; i < positions.length; i++) {
          for (let j = i + 1; j < positions.length; j++) {
            drawLine(positions[i], positions[j]);
          }
        }
      } else if (props.topologyType === "ring") {
        for (let i = 0; i < positions.length; i++) {
          drawLine(positions[i], positions[(i + 1) % positions.length]);
        }
      } else if (props.topologyType === "star") {
        for (let i = 1; i < positions.length; i++) {
          drawLine(positions[0], positions[i]);
        }
      } else if (props.topologyType === "tree") {
        for (let i = 0; i < positions.length; i++) {
          const leftChild = 2 * i + 1;
          const rightChild = 2 * i + 2;
          if (leftChild < positions.length)
            drawLine(positions[i], positions[leftChild]);
          if (rightChild < positions.length)
            drawLine(positions[i], positions[rightChild]);
        }
      }
      drawNodes();
    };

    const animatePhase = (messages, doneCallback) => {
      let completed = 0;
      const total = messages.length;
      const animations = [];
      const processedIds = new Set();

      // 计算基础动画步数
      const baseSteps = 83;
      const speedFactor = parseFloat(props.animationSpeed || "1.0");
      const baseAdjustedSteps = Math.round(baseSteps / speedFactor);

      // 为每个消息创建动画
      messages.forEach(msg => {
        if (!msg.path || !msg.path.nodes || msg.path.nodes.length === 0) return;
        
        // 为每个消息生成一个随机速度增益 (0.8 到 1.6 之间)
        const randomSpeedFactor = 0.8 + Math.random() * 0.8;
        const adjustedSteps = Math.round(baseAdjustedSteps / randomSpeedFactor);
        
        animations.push({
          msg: msg,
          path: msg.path.nodes,
          probs: msg.path.probabilities,
          currentSegment: 0,
          frame: 0,
          steps: adjustedSteps,
          src: msg.src,
          dst: msg.dst,
          isComplete: false,
          id: `${msg.src}-${msg.dst}-${msg.value}-${msg.tampered}`
        });
      });

      const animateStep = () => {
        // 如果动画被取消，直接返回
        if (!currentAnimationFrame.value) return;

        ctx.value.clearRect(0, 0, 600, 600);
        drawTopology();

        let stillAnimating = false;
        animations.forEach(anim => {
          if (!anim.isComplete) {
            if (anim.currentSegment < anim.path.length - 1) {
              stillAnimating = true;
              const start = nodePositions.value[anim.path[anim.currentSegment]];
              const end = nodePositions.value[anim.path[anim.currentSegment + 1]];
              const progress = anim.frame / anim.steps;

              const x = start.x + (end.x - start.x) * progress;
              const y = start.y + (end.y - start.y) * progress;

              ctx.value.beginPath();
              ctx.value.arc(x, y, 8, 0, Math.PI * 2);
              ctx.value.fillStyle = anim.msg.value === 0 ? "green" : "red";
              ctx.value.fill();
              ctx.value.strokeStyle = "white";
              ctx.value.lineWidth = 2;
              ctx.value.stroke();

              ctx.value.fillStyle = "black";
              ctx.value.font = "12px Arial";
              const infoText = `${anim.src}→${anim.dst}`;
              ctx.value.fillText(infoText, x + 15, y + 5);

              const probText = `P=${anim.probs[anim.currentSegment].toFixed(2)}`;
              ctx.value.fillText(probText, x + 10, y - 10);

              anim.frame++;
              if (anim.frame >= anim.steps) {
                anim.frame = 0;
                anim.currentSegment++;
              }
            } else {
              anim.isComplete = true;
              stillAnimating = true;
            }
          }
        });

        if (stillAnimating) {
          currentAnimationFrame.value = requestAnimationFrame(animateStep);
        } else {
          completed = total;
          if (completed === total && doneCallback) {
            doneCallback();
          }
        }
      };

      currentAnimationFrame.value = requestAnimationFrame(animateStep);
    };

    const startAnimation = () => {
      // 取消之前的动画
      if (currentAnimationFrame.value) {
        cancelAnimationFrame(currentAnimationFrame.value);
        currentAnimationFrame.value = null;
      }

      const simulationResult = props.simulationResult;
      if (!simulationResult) return;

      const prePrepareMessages = simulationResult.pre_prepare;
      const prepareMessages = simulationResult.prepare
        .flat()
        .filter(msg => msg.src !== 0);
      const commitMessages = simulationResult.commit.flat();

      const speedFactor = parseFloat(props.animationSpeed || "1.0");
      const pauseDuration = Math.round(800 / speedFactor);

      animatePhase(prePrepareMessages, () => {
        setTimeout(() => {
          animatePhase(prepareMessages, () => {
            setTimeout(() => {
              animatePhase(commitMessages, () => {
                setTimeout(() => {
                  finalConsensus.value = simulationResult.consensus || "共识结果已达成";
                }, pauseDuration);
              });
            }, pauseDuration);
          });
        }, pauseDuration);
      });
    };

    onMounted(() => {
      ctx.value = canvas.value.getContext("2d");
      drawTopology();
    });

    watch(
      () => props.simulationResult,
      (newResult) => {
        if (newResult) {
          startAnimation();
        }
      }
    );

    // 添加对拓扑结构变化的监听
    watch(
      [() => props.topologyType, () => props.nodeCount, () => props.byzantineNodes],
      () => {
        // 取消当前动画
        if (currentAnimationFrame.value) {
          cancelAnimationFrame(currentAnimationFrame.value);
          currentAnimationFrame.value = null;
        }
        // 清空共识结果
        finalConsensus.value = "";
        // 重新绘制拓扑
        drawTopology();
      }
    );

    return { canvas, startAnimation, finalConsensus };
  }
};
</script>

<style>
.canvas-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.consensus-result {
  margin-top: 20px;
  text-align: center;
  font-size: 16px;
  color: #333;
}
</style>

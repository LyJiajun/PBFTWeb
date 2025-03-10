<template>
  <div class="app-container">
    <!-- 左侧：表单侧边栏 -->
    <div class="left-container">
      <Form @send-topology-data="updateTopology" />
    </div>

    <!-- 中间：拓扑图区域 -->
    <div class="middle-container">
      <Topology
        ref="topologyRef"
        :topologyType="topologyType"
        :nodeCount="nodeCount"
        :byzantineNodes="byzantineNodes"
        :simulationResult="filteredSimulationResult"
      />
    </div>

    <!-- 右侧：结果侧边栏 -->
    <div class="right-container">
      <PBFTTable :filteredSimulationResult="filteredSimulationResult" :nodeCount="nodeCount" />
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import axios from "axios";
import Form from "./components/Form.vue";
import Topology from "./components/Topology.vue";
import PBFTTable from "./components/PBFTTable.vue";

export default {
  components: { Form, Topology, PBFTTable },
  setup() {
    const topologyRef = ref(null);
    const topologyType = ref("full");
    const nodeCount = ref(6);
    const byzantineNodes = ref(1);
    const simulationResult = ref(null);

    // 过滤后端返回的数据
    const filteredSimulationResult = computed(() => {
      if (!simulationResult.value) return null;
      return {
        pre_prepare: simulationResult.value.pre_prepare,
        prepare: simulationResult.value.prepare,
        commit: simulationResult.value.commit,
        consensus: simulationResult.value.consensus,
      };
    });

    const updateTopology = async (formData) => {
      topologyType.value = formData.topologyType;
      nodeCount.value = formData.nodeCount;
      byzantineNodes.value = formData.byzantineNodes;

      const requestData = {
        n: formData.nodeCount,
        m: formData.byzantineNodes,
        topology: formData.topologyType,
        n_value: 2,
        faulty_proposers: false,
        allow_tampering: false,
      };

      console.log("Request Payload to Backend:", requestData); // 打印发送给后端的数据

      console.log("当前打包时间:2024-03-10 18.17,接口路径已改 /api/simulate");
      try {
        const response = await axios.post("/api/simulate", requestData);
        simulationResult.value = response.data;
        console.log("Backend result:", JSON.stringify(filteredSimulationResult.value, null, 2));

         if (topologyRef.value) {
           topologyRef.value.startAnimation(filteredSimulationResult.value);
         }
      } catch (error) {
        console.error("Request error:", error);
      }
    };

    return {
      topologyRef,
      topologyType,
      nodeCount,
      byzantineNodes,
      simulationResult,
      filteredSimulationResult,
      updateTopology,
    };
  },
};
</script>

<style>
/* 全局重置，确保无默认外边距 */

/* 父容器：使用 Flexbox 布局，填满整个浏览器 */
.app-container {
  display: flex;
  width: 100vw;
  height: 100vh;
  box-sizing: border-box;
}

/* 左侧侧边栏：固定宽度，背景色深色，内容贴边 */
.left-container {
  flex: 0 0 320px;
  background-color: #2c3e50;  /* 深色背景 */
  color: #ecf0f1;           /* 浅色文字 */
  box-sizing: border-box;
  overflow-y: auto;
  padding: 20px;
}

/* 中间区域：拓扑图区域，占据剩余空间 */
.middle-container {
  flex: 1;
  background-color: #fff;
  box-sizing: border-box;
  overflow: auto;
  padding: 0;
  text-align: center;
  border-right: 1px solid #ccc;
}

/* 右侧侧边栏：固定宽度，背景色浅色，内容贴边 */
.right-container {
  flex: 0 0 650px;
  background-color: #fce4ec;  /* 浅粉背景 */
  box-sizing: border-box;
  overflow-y: auto;
  padding: 0;
}
</style>

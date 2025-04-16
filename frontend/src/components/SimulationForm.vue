<template>
  <div class="form-container">
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="topology">拓扑结构：</label>
        <select id="topology" v-model="formData.topology">
          <option value="full">全连接</option>
          <option value="ring">环形</option>
          <option value="star">星型</option>
          <option value="tree">树型</option>
        </select>
      </div>

      <div class="form-group">
        <label for="nodeCount">节点数量：</label>
        <input
          type="number"
          id="nodeCount"
          v-model="formData.nodeCount"
          min="4"
          max="10"
        />
      </div>

      <div class="form-group">
        <label for="byzantineNodes">拜占庭节点数量：</label>
        <input
          type="number"
          id="byzantineNodes"
          v-model="formData.byzantineNodes"
          min="0"
          :max="maxByzantineNodes"
        />
      </div>

      <div class="form-group">
        <label for="maliciousOrigin">恶意提议者：</label>
        <input
          type="checkbox"
          id="maliciousOrigin"
          v-model="formData.maliciousOrigin"
        />
      </div>

      <div class="form-group">
        <label for="falsehoodMessage">允许消息篡改：</label>
        <input
          type="checkbox"
          id="falsehoodMessage"
          v-model="formData.falsehoodMessage"
        />
      </div>

      <div class="form-group">
        <label for="animationSpeed">动画速度：</label>
        <select id="animationSpeed" v-model="formData.animationSpeed">
          <option value="0.3">慢速 (0.3x)</option>
          <option value="0.6">中速 (0.6x)</option>
          <option value="1.0">正常 (1.0x)</option>
          <option value="1.5">快速 (1.5x)</option>
          <option value="2.0">极速 (2.0x)</option>
        </select>
      </div>

      <button type="submit">开始模拟</button>
    </form>
  </div>
</template>

<script>
import { ref, computed } from "vue";

export default {
  name: "SimulationForm",
  emits: ["submit"],
  setup(props, { emit }) {
    const formData = ref({
      topology: "full",
      nodeCount: 4,
      byzantineNodes: 1,
      maliciousOrigin: false,
      falsehoodMessage: false,
      animationSpeed: "1.0"  // 添加动画速度选项
    });

    const maxByzantineNodes = computed(() => {
      return Math.floor((formData.value.nodeCount - 1) / 3);
    });

    const handleSubmit = () => {
      emit("submit", formData.value);
    };

    return {
      formData,
      maxByzantineNodes,
      handleSubmit,
    };
  },
};
</script>

<style scoped>
.form-container {
  max-width: 500px;
  margin: 0 auto;
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
}

input[type="number"],
select {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

input[type="checkbox"] {
  margin-right: 5px;
}

button {
  width: 100%;
  padding: 10px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}
</style> 
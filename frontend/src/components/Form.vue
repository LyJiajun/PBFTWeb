<template>
  <div class="form-container">
    <h3>Parameters</h3>
    <form @submit.prevent="submitForm">
      <label>Nodes:</label>
      <input type="number" v-model="formData.nodeCount" min="3" required />

      <label>Byzantine Nodes:</label>
      <input type="number" v-model="formData.byzantineNodes" min="0" required />
        <label>Topology:</label>
        <select v-model="formData.topologyType">
        <option value="full">全连接</option>
        <option value="ring">环形</option>
        <option value="star">星型</option>
        <option value="tree">树型</option>
        </select>
      


      <button type="submit">Execute</button>
    </form>
  </div>
</template>


<script>

  

import { ref } from "vue";

export default {
  emits: ["send-topology-data"],
  setup(_, { emit }) {
    const formData = ref({
      nodeCount: 6,         // 默认节点数
      byzantineNodes: 1,    // 默认拜占庭节点数
      topologyType: "full", // 默认拓扑类型
    });

    const submitForm = () => {
      emit("send-topology-data", formData.value);
    };

    return { formData, submitForm };
  },
};
</script>

<style>
.form-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
form {
  width: 100%;
  display: flex;
  flex-direction: column;
}
label {
  margin-top: 10px;
}
input, select {
  width: 100%;
  padding: 8px;
  margin-top: 5px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: white;
  font-size: 14px;
  appearance: none; /* 去掉默认样式 */
}
button {
  margin-top: 10px;
  padding: 10px;
  background-color: #42b983;
  color: white;
  border: none;
  cursor: pointer;
  width: 100%;
}
button:hover {
  background-color: #369b72;
}
</style>

<template>
  <div class="form-container">
    <h2>PBFT Simulation Parameters</h2>
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="topologyType">Topology:</label>
        <select id="topologyType" v-model="formData.topologyType">
          <option value="full">Fully Connected</option>
          <option value="ring">Ring</option>
          <option value="star">Star</option>
          <option value="tree">Tree</option>
        </select>
      </div>

      <div class="form-group">
        <label for="nodeCount">Number of Nodes:</label>
        <input
          type="number"
          id="nodeCount"
          v-model="formData.nodeCount"
          min="4"
          max="10"
        />
      </div>

      <div class="form-group">
        <label for="byzantineNodes">Number of Byzantine Nodes:</label>
        <input
          type="number"
          id="byzantineNodes"
          v-model="formData.byzantineNodes"
          min="0"
          :max="maxByzantineNodes"
        />
      </div>

      <div class="form-group">
        <label for="messageDeliveryProb">Message Delivery Probability:</label>
        <input
          type="number"
          id="messageDeliveryProb"
          v-model="formData.messageDeliveryProb"
          min="0"
          max="1"
          step="0.1"
        />
      </div>

      <div class="form-group">
        <label for="animationSpeed">Animation Speed:</label>
        <select id="animationSpeed" v-model="formData.animationSpeed">
          <option value="0.3">Slow (0.3x)</option>
          <option value="0.6">Medium (0.6x)</option>
          <option value="1.0">Normal (1.0x)</option>
          <option value="1.5">Fast (1.5x)</option>
          <option value="2.0">Very Fast (2.0x)</option>
        </select>
      </div>

      <button type="submit">Start Simulation</button>
    </form>
  </div>
</template>

<script>
import { ref, computed } from "vue";

export default {
  name: "Form",
  emits: ["send-topology-data"],
  setup(props, { emit }) {
    const formData = ref({
      topologyType: "full",
      nodeCount: 6,
      byzantineNodes: 1,
      messageDeliveryProb: 1.0,
      animationSpeed: "1.0"
    });

    const maxByzantineNodes = computed(() => {
      return formData.value.nodeCount - 1;
    });

    const handleSubmit = () => {
      emit("send-topology-data", formData.value);
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
  color: #ecf0f1;
}

h2 {
  margin-bottom: 20px;
  text-align: center;
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
  border: 1px solid #3498db;
  border-radius: 4px;
  background-color: #2c3e50;
  color: #ecf0f1;
  transition: all 0.3s ease;
}

input[type="number"]:focus,
select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%233498db'%3e%3cpath d='M7 10l5 5 5-5z'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 16px;
  padding-right: 30px;
  cursor: pointer;
}

input[type="number"]::-webkit-inner-spin-button,
input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type="number"] {
  -moz-appearance: textfield;
}

button {
  width: 100%;
  padding: 10px;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 20px;
}

button:hover {
  background-color: #2980b9;
}
</style>

<script>
export default {
  onLaunch() {},
  onShow() { uni.$emit('rokicar-app-show'); },
  onHide() { uni.$emit('rokicar-app-hide'); },
};
</script>

<style>
page { min-height: 100%; background: #f4f6f3; color: #152019; }
button::after { border: 0; }
</style>

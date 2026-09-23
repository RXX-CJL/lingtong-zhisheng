// pages/submit/submit.js
const app = getApp();
const api = require('../../utils/api.js');
const { getTypeList } = require('../../utils/format.js');

Page({
  data: {
    images: [],           // 图片本地临时路径数组
    selectedType: '',     // 选中的违规类型
    remark: '',           // 补充说明
    typeList: getTypeList(),  // 违规类型列表
    submitting: false     // 提交中状态
  },

  onLoad(options) {
    console.log('提交页加载', options);
  },

  /**
   * 选择图片
   */
  chooseImage() {
    const count = 3 - this.data.images.length;
    if (count <= 0) {
      wx.showToast({
        title: '最多上传3张图片',
        icon: 'none'
      });
      return;
    }

    wx.chooseMedia({
      count: count,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFiles = res.tempFiles;
        const newImages = tempFiles.map(file => file.tempFilePath);
        this.setData({
          images: [...this.data.images, ...newImages]
        });
      },
      fail: (err) => {
        console.error('选择图片失败', err);
        wx.showToast({
          title: '请选择图片',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 移除图片
   */
  removeImage(e) {
    const index = e.currentTarget.dataset.index;
    const images = [...this.data.images];
    images.splice(index, 1);
    this.setData({ images });
  },

  /**
   * 预览图片
   */
  previewImage(e) {
    const index = e.currentTarget.dataset.index;
    wx.previewImage({
      current: this.data.images[index],
      urls: this.data.images
    });
  },

  /**
   * 选择违规类型
   */
  selectType(e) {
    const type = e.currentTarget.dataset.type;
    this.setData({ selectedType: type });
  },

  /**
   * 备注输入
   */
  onRemarkInput(e) {
    this.setData({
      remark: e.detail.value
    });
  },

  /**
   * 提交举报
   */
  submit() {
    // 校验
    if (this.data.images.length === 0) {
      wx.showToast({
        title: '请上传至少一张图片',
        icon: 'none'
      });
      return;
    }

    if (!this.data.selectedType) {
      wx.showToast({
        title: '请选择违规类型',
        icon: 'none'
      });
      return;
    }

    if (this.data.submitting) {
      return;
    }

    this.setData({ submitting: true });

    // 显示加载提示
    wx.showLoading({
      title: '正在提交...',
      mask: true
    });

    // 将图片转换为 base64
    const imagePromises = this.data.images.map(imagePath => {
      return this.convertImageToBase64(imagePath);
    });

    Promise.all(imagePromises)
      .then(imagesBase64 => {
        const openid = app.globalData.openid;
        const violationData = {
          violation_type: this.data.selectedType,
          confidence: 0.95,
          remark: this.data.remark
        };

        return api.submitViolation(openid, violationData, imagesBase64);
      })
      .then(res => {
        wx.hideLoading();
        console.log('提交成功', res);
        wx.showToast({
          title: '已提交，待审核',
          icon: 'success',
          duration: 2000
        });

        // 延迟返回
        setTimeout(() => {
          wx.navigateBack();
        }, 2000);
      })
      .catch(err => {
        wx.hideLoading();
        console.error('提交失败', err);
        this.setData({ submitting: false });
        wx.showToast({
          title: '提交失败，请重试',
          icon: 'none'
        });
      });
  },

  /**
   * 将图片转换为 base64（不带 data:image 前缀）
   */
  convertImageToBase64(imagePath) {
    return new Promise((resolve, reject) => {
      wx.getFileSystemManager().readFile({
        filePath: imagePath,
        encoding: 'base64',
        success: (res) => {
          resolve(res.data);
        },
        fail: (err) => {
          console.error('图片读取失败', err);
          reject(err);
        }
      });
    });
  },

  /**
   * 页面错误处理
   */
  onError(err) {
    console.error('页面错误', err);
    wx.showToast({
      title: '页面加载异常',
      icon: 'none'
    });
  }
});
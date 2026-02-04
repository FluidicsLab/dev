
namespace GigeCameraCtrlSample
{
    partial class Form1
    {
        /// <summary>
        /// 必要なデザイナー変数です。
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// 使用中のリソースをすべてクリーンアップします。
        /// </summary>
        /// <param name="disposing">マネージド リソースを破棄する場合は true を指定し、その他の場合は false を指定します。</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows フォーム デザイナーで生成されたコード

        /// <summary>
        /// デザイナー サポートに必要なメソッドです。このメソッドの内容を
        /// コード エディターで変更しないでください。
        /// </summary>
        private void InitializeComponent()
        {
            this.button_clear = new System.Windows.Forms.Button();
            this.groupBoxCameraParam = new System.Windows.Forms.GroupBox();
            this.buttonGetBinningDivider = new System.Windows.Forms.Button();
            this.comboBoxBinningDivider = new System.Windows.Forms.ComboBox();
            this.buttonSetBinningDivider = new System.Windows.Forms.Button();
            this.label5 = new System.Windows.Forms.Label();
            this.buttonGetBinningType = new System.Windows.Forms.Button();
            this.buttonGetHeight = new System.Windows.Forms.Button();
            this.buttonSetHeight = new System.Windows.Forms.Button();
            this.buttonGetWidth = new System.Windows.Forms.Button();
            this.buttonSetWidth = new System.Windows.Forms.Button();
            this.buttonGetGain = new System.Windows.Forms.Button();
            this.textBoxHeight = new System.Windows.Forms.TextBox();
            this.label4 = new System.Windows.Forms.Label();
            this.textBoxWidth = new System.Windows.Forms.TextBox();
            this.label3 = new System.Windows.Forms.Label();
            this.comboBoxBinningType = new System.Windows.Forms.ComboBox();
            this.buttonSetBinningType = new System.Windows.Forms.Button();
            this.label2 = new System.Windows.Forms.Label();
            this.buttonSetGain = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.textBoxGain = new System.Windows.Forms.TextBox();
            this.groupBoxAcquisition = new System.Windows.Forms.GroupBox();
            this.btnContinuousStop = new System.Windows.Forms.Button();
            this.btnContinuousStart = new System.Windows.Forms.Button();
            this.btnSingleFrameStart = new System.Windows.Forms.Button();
            this.groupBox_Connect = new System.Windows.Forms.GroupBox();
            this.buttonDisConnect = new System.Windows.Forms.Button();
            this.buttonConnect = new System.Windows.Forms.Button();
            this.pictureBox1 = new System.Windows.Forms.PictureBox();
            this.textBoxInfo = new System.Windows.Forms.TextBox();
            this.comboBoxDetectList = new System.Windows.Forms.ComboBox();
            this.buttonDetect = new System.Windows.Forms.Button();
            this.groupBoxCameraParam.SuspendLayout();
            this.groupBoxAcquisition.SuspendLayout();
            this.groupBox_Connect.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).BeginInit();
            this.SuspendLayout();
            //
            // button_clear
            //
            this.button_clear.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right)));
            this.button_clear.Location = new System.Drawing.Point(913, 440);
            this.button_clear.Name = "button_clear";
            this.button_clear.Size = new System.Drawing.Size(42, 23);
            this.button_clear.TabIndex = 23;
            this.button_clear.Text = "clear";
            this.button_clear.UseVisualStyleBackColor = true;
            this.button_clear.Click += new System.EventHandler(this.button_clear_Click);
            //
            // groupBoxCameraParam
            //
            this.groupBoxCameraParam.Controls.Add(this.buttonGetBinningDivider);
            this.groupBoxCameraParam.Controls.Add(this.comboBoxBinningDivider);
            this.groupBoxCameraParam.Controls.Add(this.buttonSetBinningDivider);
            this.groupBoxCameraParam.Controls.Add(this.label5);
            this.groupBoxCameraParam.Controls.Add(this.buttonGetBinningType);
            this.groupBoxCameraParam.Controls.Add(this.buttonGetHeight);
            this.groupBoxCameraParam.Controls.Add(this.buttonSetHeight);
            this.groupBoxCameraParam.Controls.Add(this.buttonGetWidth);
            this.groupBoxCameraParam.Controls.Add(this.buttonSetWidth);
            this.groupBoxCameraParam.Controls.Add(this.buttonGetGain);
            this.groupBoxCameraParam.Controls.Add(this.textBoxHeight);
            this.groupBoxCameraParam.Controls.Add(this.label4);
            this.groupBoxCameraParam.Controls.Add(this.textBoxWidth);
            this.groupBoxCameraParam.Controls.Add(this.label3);
            this.groupBoxCameraParam.Controls.Add(this.comboBoxBinningType);
            this.groupBoxCameraParam.Controls.Add(this.buttonSetBinningType);
            this.groupBoxCameraParam.Controls.Add(this.label2);
            this.groupBoxCameraParam.Controls.Add(this.buttonSetGain);
            this.groupBoxCameraParam.Controls.Add(this.label1);
            this.groupBoxCameraParam.Controls.Add(this.textBoxGain);
            this.groupBoxCameraParam.Enabled = false;
            this.groupBoxCameraParam.Location = new System.Drawing.Point(10, 207);
            this.groupBoxCameraParam.Name = "groupBoxCameraParam";
            this.groupBoxCameraParam.Size = new System.Drawing.Size(373, 217);
            this.groupBoxCameraParam.TabIndex = 22;
            this.groupBoxCameraParam.TabStop = false;
            this.groupBoxCameraParam.Text = "CameraParam";
            //
            // buttonGetBinningDivider
            //
            this.buttonGetBinningDivider.Location = new System.Drawing.Point(314, 158);
            this.buttonGetBinningDivider.Name = "buttonGetBinningDivider";
            this.buttonGetBinningDivider.Size = new System.Drawing.Size(45, 19);
            this.buttonGetBinningDivider.TabIndex = 26;
            this.buttonGetBinningDivider.Text = "Get";
            this.buttonGetBinningDivider.UseVisualStyleBackColor = true;
            this.buttonGetBinningDivider.Click += new System.EventHandler(this.buttonGetBinningDivider_Click);
            //
            // comboBoxBinningDivider
            //
            this.comboBoxBinningDivider.FormattingEnabled = true;
            this.comboBoxBinningDivider.Location = new System.Drawing.Point(85, 157);
            this.comboBoxBinningDivider.Name = "comboBoxBinningDivider";
            this.comboBoxBinningDivider.Size = new System.Drawing.Size(170, 20);
            this.comboBoxBinningDivider.TabIndex = 25;
            //
            // buttonSetBinningDivider
            //
            this.buttonSetBinningDivider.Location = new System.Drawing.Point(263, 158);
            this.buttonSetBinningDivider.Name = "buttonSetBinningDivider";
            this.buttonSetBinningDivider.Size = new System.Drawing.Size(45, 19);
            this.buttonSetBinningDivider.TabIndex = 24;
            this.buttonSetBinningDivider.Text = "Set";
            this.buttonSetBinningDivider.UseVisualStyleBackColor = true;
            this.buttonSetBinningDivider.Click += new System.EventHandler(this.buttonSetBinningDivider_Click);
            //
            // label5
            //
            this.label5.AutoSize = true;
            this.label5.Location = new System.Drawing.Point(6, 142);
            this.label5.Name = "label5";
            this.label5.Size = new System.Drawing.Size(179, 12);
            this.label5.TabIndex = 23;
            this.label5.Text = "Binning Divider (Enumerate Node)";
            //
            // buttonGetBinningType
            //
            this.buttonGetBinningType.Location = new System.Drawing.Point(314, 120);
            this.buttonGetBinningType.Name = "buttonGetBinningType";
            this.buttonGetBinningType.Size = new System.Drawing.Size(45, 19);
            this.buttonGetBinningType.TabIndex = 22;
            this.buttonGetBinningType.Text = "Get";
            this.buttonGetBinningType.UseVisualStyleBackColor = true;
            this.buttonGetBinningType.Click += new System.EventHandler(this.buttonGetBinningType_Click);
            //
            // buttonGetHeight
            //
            this.buttonGetHeight.Location = new System.Drawing.Point(314, 42);
            this.buttonGetHeight.Name = "buttonGetHeight";
            this.buttonGetHeight.Size = new System.Drawing.Size(45, 21);
            this.buttonGetHeight.TabIndex = 21;
            this.buttonGetHeight.Text = "Get";
            this.buttonGetHeight.UseVisualStyleBackColor = true;
            this.buttonGetHeight.Click += new System.EventHandler(this.buttonGetHeight_Click);
            //
            // buttonSetHeight
            //
            this.buttonSetHeight.Location = new System.Drawing.Point(263, 42);
            this.buttonSetHeight.Name = "buttonSetHeight";
            this.buttonSetHeight.Size = new System.Drawing.Size(45, 21);
            this.buttonSetHeight.TabIndex = 20;
            this.buttonSetHeight.Text = "Set";
            this.buttonSetHeight.UseVisualStyleBackColor = true;
            this.buttonSetHeight.Click += new System.EventHandler(this.buttonSetHeight_Click);
            //
            // buttonGetWidth
            //
            this.buttonGetWidth.Location = new System.Drawing.Point(314, 17);
            this.buttonGetWidth.Name = "buttonGetWidth";
            this.buttonGetWidth.Size = new System.Drawing.Size(45, 21);
            this.buttonGetWidth.TabIndex = 19;
            this.buttonGetWidth.Text = "Get";
            this.buttonGetWidth.UseVisualStyleBackColor = true;
            this.buttonGetWidth.Click += new System.EventHandler(this.buttonGetWidth_Click);
            //
            // buttonSetWidth
            //
            this.buttonSetWidth.Location = new System.Drawing.Point(263, 17);
            this.buttonSetWidth.Name = "buttonSetWidth";
            this.buttonSetWidth.Size = new System.Drawing.Size(45, 21);
            this.buttonSetWidth.TabIndex = 18;
            this.buttonSetWidth.Text = "Set";
            this.buttonSetWidth.UseVisualStyleBackColor = true;
            this.buttonSetWidth.Click += new System.EventHandler(this.buttonSetWidth_Click);
            //
            // buttonGetGain
            //
            this.buttonGetGain.Location = new System.Drawing.Point(314, 67);
            this.buttonGetGain.Name = "buttonGetGain";
            this.buttonGetGain.Size = new System.Drawing.Size(45, 21);
            this.buttonGetGain.TabIndex = 17;
            this.buttonGetGain.Text = "Get";
            this.buttonGetGain.UseVisualStyleBackColor = true;
            this.buttonGetGain.Click += new System.EventHandler(this.buttonGetGain_Click);
            //
            // textBoxHeight
            //
            this.textBoxHeight.Location = new System.Drawing.Point(174, 43);
            this.textBoxHeight.Name = "textBoxHeight";
            this.textBoxHeight.Size = new System.Drawing.Size(81, 19);
            this.textBoxHeight.TabIndex = 16;
            this.textBoxHeight.Text = "1024";
            //
            // label4
            //
            this.label4.AutoSize = true;
            this.label4.Location = new System.Drawing.Point(6, 46);
            this.label4.Name = "label4";
            this.label4.Size = new System.Drawing.Size(115, 12);
            this.label4.TabIndex = 15;
            this.label4.Text = "Height (Integer Node)";
            //
            // textBoxWidth
            //
            this.textBoxWidth.Location = new System.Drawing.Point(174, 18);
            this.textBoxWidth.Name = "textBoxWidth";
            this.textBoxWidth.Size = new System.Drawing.Size(81, 19);
            this.textBoxWidth.TabIndex = 14;
            this.textBoxWidth.Text = "1280";
            //
            // label3
            //
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(6, 21);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(110, 12);
            this.label3.TabIndex = 13;
            this.label3.Text = "Width (Integer Node)";
            //
            // comboBoxBinningType
            //
            this.comboBoxBinningType.FormattingEnabled = true;
            this.comboBoxBinningType.Location = new System.Drawing.Point(85, 119);
            this.comboBoxBinningType.Name = "comboBoxBinningType";
            this.comboBoxBinningType.Size = new System.Drawing.Size(170, 20);
            this.comboBoxBinningType.TabIndex = 12;
            //
            // buttonSetBinningType
            //
            this.buttonSetBinningType.Location = new System.Drawing.Point(263, 120);
            this.buttonSetBinningType.Name = "buttonSetBinningType";
            this.buttonSetBinningType.Size = new System.Drawing.Size(45, 19);
            this.buttonSetBinningType.TabIndex = 11;
            this.buttonSetBinningType.Text = "Set";
            this.buttonSetBinningType.UseVisualStyleBackColor = true;
            this.buttonSetBinningType.Click += new System.EventHandler(this.buttonSetBinningType_Click);
            //
            // label2
            //
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(6, 104);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(168, 12);
            this.label2.TabIndex = 9;
            this.label2.Text = "Binning Type (Enumerate Node)";
            //
            // buttonSetGain
            //
            this.buttonSetGain.Location = new System.Drawing.Point(263, 67);
            this.buttonSetGain.Name = "buttonSetGain";
            this.buttonSetGain.Size = new System.Drawing.Size(45, 21);
            this.buttonSetGain.TabIndex = 7;
            this.buttonSetGain.Text = "Set";
            this.buttonSetGain.UseVisualStyleBackColor = true;
            this.buttonSetGain.Click += new System.EventHandler(this.buttonSetGain_Click);
            //
            // label1
            //
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(6, 71);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(93, 12);
            this.label1.TabIndex = 8;
            this.label1.Text = "Gain (float Node)";
            //
            // textBoxGain
            //
            this.textBoxGain.Location = new System.Drawing.Point(174, 68);
            this.textBoxGain.Name = "textBoxGain";
            this.textBoxGain.Size = new System.Drawing.Size(81, 19);
            this.textBoxGain.TabIndex = 6;
            this.textBoxGain.Text = "1.0";
            //
            // groupBoxAcquisition
            //
            this.groupBoxAcquisition.Controls.Add(this.btnContinuousStop);
            this.groupBoxAcquisition.Controls.Add(this.btnContinuousStart);
            this.groupBoxAcquisition.Controls.Add(this.btnSingleFrameStart);
            this.groupBoxAcquisition.Enabled = false;
            this.groupBoxAcquisition.Location = new System.Drawing.Point(10, 126);
            this.groupBoxAcquisition.Name = "groupBoxAcquisition";
            this.groupBoxAcquisition.Size = new System.Drawing.Size(373, 75);
            this.groupBoxAcquisition.TabIndex = 21;
            this.groupBoxAcquisition.TabStop = false;
            this.groupBoxAcquisition.Text = "Acquisition";
            //
            // btnContinuousStop
            //
            this.btnContinuousStop.Location = new System.Drawing.Point(263, 19);
            this.btnContinuousStop.Margin = new System.Windows.Forms.Padding(2);
            this.btnContinuousStop.Name = "btnContinuousStop";
            this.btnContinuousStop.Size = new System.Drawing.Size(105, 47);
            this.btnContinuousStop.TabIndex = 5;
            this.btnContinuousStop.Text = "Continuous Stop";
            this.btnContinuousStop.UseVisualStyleBackColor = true;
            this.btnContinuousStop.Click += new System.EventHandler(this.btnContinuousStop_Click);
            //
            // btnContinuousStart
            //
            this.btnContinuousStart.Location = new System.Drawing.Point(154, 19);
            this.btnContinuousStart.Margin = new System.Windows.Forms.Padding(2);
            this.btnContinuousStart.Name = "btnContinuousStart";
            this.btnContinuousStart.Size = new System.Drawing.Size(105, 47);
            this.btnContinuousStart.TabIndex = 4;
            this.btnContinuousStart.Text = "Continuous Start";
            this.btnContinuousStart.UseVisualStyleBackColor = true;
            this.btnContinuousStart.Click += new System.EventHandler(this.btnContinuousStart_Click);
            //
            // btnSingleFrameStart
            //
            this.btnSingleFrameStart.Location = new System.Drawing.Point(5, 17);
            this.btnSingleFrameStart.Margin = new System.Windows.Forms.Padding(2);
            this.btnSingleFrameStart.Name = "btnSingleFrameStart";
            this.btnSingleFrameStart.Size = new System.Drawing.Size(105, 49);
            this.btnSingleFrameStart.TabIndex = 3;
            this.btnSingleFrameStart.Text = "Single";
            this.btnSingleFrameStart.UseVisualStyleBackColor = true;
            this.btnSingleFrameStart.Click += new System.EventHandler(this.btnSingleFrameStart_Click);
            //
            // groupBox_Connect
            //
            this.groupBox_Connect.Controls.Add(this.buttonDetect);
            this.groupBox_Connect.Controls.Add(this.buttonDisConnect);
            this.groupBox_Connect.Controls.Add(this.comboBoxDetectList);
            this.groupBox_Connect.Controls.Add(this.buttonConnect);
            this.groupBox_Connect.Location = new System.Drawing.Point(10, 11);
            this.groupBox_Connect.Name = "groupBox_Connect";
            this.groupBox_Connect.Size = new System.Drawing.Size(373, 109);
            this.groupBox_Connect.TabIndex = 20;
            this.groupBox_Connect.TabStop = false;
            this.groupBox_Connect.Text = "Connect/DisConnect";
            //
            // buttonDisConnect
            //
            this.buttonDisConnect.Enabled = false;
            this.buttonDisConnect.Location = new System.Drawing.Point(192, 55);
            this.buttonDisConnect.Margin = new System.Windows.Forms.Padding(2);
            this.buttonDisConnect.Name = "buttonDisConnect";
            this.buttonDisConnect.Size = new System.Drawing.Size(107, 49);
            this.buttonDisConnect.TabIndex = 1;
            this.buttonDisConnect.Text = "DisConnect";
            this.buttonDisConnect.UseVisualStyleBackColor = true;
            this.buttonDisConnect.Click += new System.EventHandler(this.buttonDisConnect_Click);
            //
            // buttonConnect
            //
            this.buttonConnect.Enabled = false;
            this.buttonConnect.Location = new System.Drawing.Point(78, 55);
            this.buttonConnect.Margin = new System.Windows.Forms.Padding(2);
            this.buttonConnect.Name = "buttonConnect";
            this.buttonConnect.Size = new System.Drawing.Size(107, 49);
            this.buttonConnect.TabIndex = 0;
            this.buttonConnect.Text = "Connect";
            this.buttonConnect.UseVisualStyleBackColor = true;
            this.buttonConnect.Click += new System.EventHandler(this.buttonConnect_Click);
            //
            // pictureBox1
            //
            this.pictureBox1.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom)
            | System.Windows.Forms.AnchorStyles.Left)
            | System.Windows.Forms.AnchorStyles.Right)));
            this.pictureBox1.Location = new System.Drawing.Point(388, 11);
            this.pictureBox1.Margin = new System.Windows.Forms.Padding(2);
            this.pictureBox1.Name = "pictureBox1";
            this.pictureBox1.Size = new System.Drawing.Size(567, 413);
            this.pictureBox1.TabIndex = 19;
            this.pictureBox1.TabStop = false;
            //
            // textBoxInfo
            //
            this.textBoxInfo.Anchor = ((System.Windows.Forms.AnchorStyles)(((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left)
            | System.Windows.Forms.AnchorStyles.Right)));
            this.textBoxInfo.Location = new System.Drawing.Point(10, 440);
            this.textBoxInfo.Margin = new System.Windows.Forms.Padding(2);
            this.textBoxInfo.Multiline = true;
            this.textBoxInfo.Name = "textBoxInfo";
            this.textBoxInfo.ScrollBars = System.Windows.Forms.ScrollBars.Vertical;
            this.textBoxInfo.Size = new System.Drawing.Size(898, 143);
            this.textBoxInfo.TabIndex = 18;
            //
            // comboBoxDetectList
            //
            this.comboBoxDetectList.Font = new System.Drawing.Font("MS UI Gothic", 12F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(128)));
            this.comboBoxDetectList.FormattingEnabled = true;
            this.comboBoxDetectList.Location = new System.Drawing.Point(89, 21);
            this.comboBoxDetectList.Name = "comboBoxDetectList";
            this.comboBoxDetectList.Size = new System.Drawing.Size(274, 24);
            this.comboBoxDetectList.TabIndex = 24;
            //
            // buttonDetect
            //
            this.buttonDetect.Location = new System.Drawing.Point(8, 20);
            this.buttonDetect.Name = "buttonDetect";
            this.buttonDetect.Size = new System.Drawing.Size(75, 27);
            this.buttonDetect.TabIndex = 25;
            this.buttonDetect.Text = "Detect";
            this.buttonDetect.UseVisualStyleBackColor = true;
            this.buttonDetect.Click += new System.EventHandler(this.buttonDetect_Click);
            //
            // Form1
            //
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 12F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(965, 594);
            this.Controls.Add(this.button_clear);
            this.Controls.Add(this.groupBoxCameraParam);
            this.Controls.Add(this.groupBoxAcquisition);
            this.Controls.Add(this.groupBox_Connect);
            this.Controls.Add(this.pictureBox1);
            this.Controls.Add(this.textBoxInfo);
            this.Name = "Form1";
            this.Text = "Sample";
            this.FormClosing += new System.Windows.Forms.FormClosingEventHandler(this.Form1_FormClosing);
            this.groupBoxCameraParam.ResumeLayout(false);
            this.groupBoxCameraParam.PerformLayout();
            this.groupBoxAcquisition.ResumeLayout(false);
            this.groupBox_Connect.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button button_clear;
        private System.Windows.Forms.GroupBox groupBoxCameraParam;
        private System.Windows.Forms.Button buttonGetBinningDivider;
        private System.Windows.Forms.ComboBox comboBoxBinningDivider;
        private System.Windows.Forms.Button buttonSetBinningDivider;
        private System.Windows.Forms.Label label5;
        private System.Windows.Forms.Button buttonGetBinningType;
        private System.Windows.Forms.Button buttonGetHeight;
        private System.Windows.Forms.Button buttonSetHeight;
        private System.Windows.Forms.Button buttonGetWidth;
        private System.Windows.Forms.Button buttonSetWidth;
        private System.Windows.Forms.Button buttonGetGain;
        private System.Windows.Forms.TextBox textBoxHeight;
        private System.Windows.Forms.Label label4;
        private System.Windows.Forms.TextBox textBoxWidth;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.ComboBox comboBoxBinningType;
        private System.Windows.Forms.Button buttonSetBinningType;
        private System.Windows.Forms.Label label2;
        private System.Windows.Forms.Button buttonSetGain;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.TextBox textBoxGain;
        private System.Windows.Forms.GroupBox groupBoxAcquisition;
        private System.Windows.Forms.Button btnContinuousStop;
        private System.Windows.Forms.Button btnContinuousStart;
        private System.Windows.Forms.Button btnSingleFrameStart;
        private System.Windows.Forms.GroupBox groupBox_Connect;
        private System.Windows.Forms.Button buttonDisConnect;
        private System.Windows.Forms.Button buttonConnect;
        private System.Windows.Forms.PictureBox pictureBox1;
        private System.Windows.Forms.TextBox textBoxInfo;
        private System.Windows.Forms.ComboBox comboBoxDetectList;
        private System.Windows.Forms.Button buttonDetect;
    }
}


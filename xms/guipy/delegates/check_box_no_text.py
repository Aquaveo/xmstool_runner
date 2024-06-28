"""Qt delegate for displaying a checkbox with no text label."""
# 1. Standard python modules

# 2. Third party modules
from PySide6.QtCore import QEvent, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QCheckBox, QStyle, QStyledItemDelegate

# 3. Aquaveo modules

# 4. Local modules


class CheckBoxNoTextDelegate(QStyledItemDelegate):
    """Qt delegate for displaying a checkbox with no text label."""
    state_changed = Signal(QModelIndex)

    def __init__(self, parent=None):
        """Initializes the class.

        Args:
            parent (Something derived from QObject): The parent object.
        """
        super().__init__(parent)
        check_size = 14
        self.checked = QPixmap(check_size, check_size)
        self.unchecked = QPixmap(check_size, check_size)
        self.disabled_checked = QPixmap(check_size, check_size)
        self.disabled_unchecked = QPixmap(check_size, check_size)

        self.checked.fill(Qt.transparent)
        self.unchecked.fill(Qt.transparent)
        self.disabled_checked.fill(Qt.transparent)
        self.disabled_unchecked.fill(Qt.transparent)

        check = QCheckBox()
        check.setCheckState(Qt.Checked)
        check.render(self.checked)
        check.setCheckState(Qt.Unchecked)
        check.render(self.unchecked)
        # disabled rendering
        checked_disabled = QCheckBox()
        checked_disabled.setCheckState(Qt.Checked)
        checked_disabled.setDisabled(True)
        checked_disabled.render(self.disabled_checked)
        unchecked_disabled = QCheckBox()
        unchecked_disabled.setCheckState(Qt.Unchecked)
        unchecked_disabled.setDisabled(True)
        unchecked_disabled.render(self.disabled_unchecked)

    def paint(self, painter, option, index):
        """Override of QStyledItemDelegate method of same name.

        Args:
            painter (QPainter): The painter.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.
        """
        if not index.isValid():
            return
        opt = option
        flags = index.flags()
        # Darken the background if disabled
        # background_color = QColor(255, 255, 255) if (flags & Qt.ItemIsEnabled) else QColor(240, 240, 240)
        if not (flags & Qt.ItemIsEnabled):
            painter.fillRect(opt.rect, QColor(240, 240, 240))
        if opt.state & QStyle.State_Selected:
            painter.fillRect(opt.rect, opt.palette.highlight())
        state = index.data(Qt.CheckStateRole)  # Used with QxPandasDataModel
        if state is None:  # Check the default role if nothing in CheckStateRole.
            state = index.data()
        pix_size = self.checked.size()
        draw_point = opt.rect.center()
        draw_point.setX(draw_point.x() - (pix_size.width() / 2))
        draw_point.setY(draw_point.y() - (pix_size.height() / 2))
        if (not opt.state & QStyle.State_Enabled) and not state:
            painter.drawPixmap(draw_point, self.disabled_unchecked)
        elif not opt.state & QStyle.State_Enabled:
            painter.drawPixmap(draw_point, self.disabled_checked)
        elif not state:
            painter.drawPixmap(draw_point, self.unchecked)
        else:
            painter.drawPixmap(draw_point, self.checked)

    def editorEvent(self, event, model, option, index):  # noqa: N802
        """Override of QStyledItemDelegate method of same name.

        Args:
            event (QEvent): The editor event that was triggered.
            model (QAbstractItemModel): The data model.
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.

        Returns:
            (bool): The whether the event was consumed.
        """
        if event.type() != QEvent.MouseButtonRelease and event.type() != QEvent.MouseButtonDblClick:
            return False
        if not index.flags() & Qt.ItemIsEnabled:
            return False
        state = index.data(Qt.CheckStateRole)  # Used with QxPandasDataModel
        if state is None:  # Check the default role if nothing in CheckStateRole.
            state = index.data()

        if not state:
            model.setData(index, True)
        else:
            model.setData(index, False)
        self.state_changed.emit(index)
        return False

    def createEditor(self, parent, option, index):  # noqa: N802
        """Override of QStyledItemDelegate method of same name.

        Args:
            parent (QWidget): the parent widget
            option (QStyleOptionViewItem): The style options.
            index (QModelIndex): The index in the model.

        Returns:
            (None): Returns None to prevent default behavior
        """
        return None
